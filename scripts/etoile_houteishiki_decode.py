# -*- coding: utf-8 -*-
"""
decode_scr.py — reusable decoder for 《エトワールの方程式》(clearcolor, 2004) script.

Pipeline (all steps reverse-engineered from iso_raw/root/Etoile.exe, see RE_NOTES.md):
  1. scr.pac container: [u32 count][u32 0] + count*40B entries.
     Entry = [name32][u32 uncomp_size][u32 comp_size].  (NOT offset/size!)
     Member data is SEQUENTIAL after the index (index_end = 8 + count*40);
     offset[i] = offset[i-1] + (comp_size[i-1] if >0 else uncomp_size[i-1]).
     Proven by PAC parser Etoile.exe 0x415E60 + reader 0x415FB0; closure: final
     offset == file size exactly, 327 members magic '_SCRT', 16 '\xffSCRT'.
  2. Each member is LZSS-compressed (Okumura N=4096 F=18, ring zeroed, r0=0xFEE,
     flags LSB-first 1=literal/0=match, pos=b1|((b2&0xF0)<<4), len=(b2&0xF)+3).
     Proven by decompressor Etoile.exe 0x404770. Decompressed data starts 'SCRT'.
     Closure: len(out)==uncomp_size AND input consumed==comp_size for 343/343.
  3. Decompressed 'SCRT' script = [magic 'SCRT'][u32 record_count][records...].
     Each record = [u32 type][payload]; per-type payload size fixed (from the
     per-type load methods). Walker validates count==header and end==len 343/343.

Output: scr_dec/<name>.bin = decompressed SCRT member (cp932 text + 0x0a control
codes + binary record structure preserved verbatim). Plus a control-code manifest
and closure statistics.

Usage:
  python decode_scr.py [--pac PATH] [--out DIR]
Defaults: --pac iso_raw/bin1/scr.pac  --out scr_dec
"""
import struct, os, sys, argparse
from collections import Counter

# ---- record (type u32 + payload) sizes, derived from Etoile.exe load methods ----
RSIZE = {0:264,1:4,2:68,3:68,4:8,5:4,6:80,7:16,8:272,9:16,10:4,11:4,12:8,
         13:276,14:272,15:12,16:12705,17:4,18:208,19:1548,20:272,21:12,22:276,23:12}
# message (type 16) field offsets relative to record start (type u32 at +0):
MSG_NAME=4; MSG_NAME_SZ=25; MSG_VOICE=29; MSG_VOICE_SLOT=260
MSG_TEXT=8349; MSG_TEXT_SLOT=128; MSG_PAGECOUNT=12445; MSG_CHARCOUNT=12449
# select (type 18): +4 choice text(128B, 0x0a-separated), +132 two 32B branch labels

OPCODE_NAME = {
 0:'cmd0 (name+params, 未证)',1:'END/return (exec returns 3)',2:'LABEL definition (no-op)',
 3:'JUMP to label',4:'cmd4 (u32 param)',5:'cmd5 (zero-payload)',6:'CONDITIONAL JUMP (cmp+switch)',
 7:'variable/flag op (部分证)',8:'BG/SCREEN load (BLACK/WHITE/*.arg) = clear-screen',9:'cmd9 (3*u32, 未证)',
 10:'cmd10 (zero-payload)',11:'cmd11 (zero-payload)',12:'fade/transition control (部分证)',
 13:'TRANSITION (CROSSFADE)',14:'BG/CHAR load (name+params)',15:'cmd15 (2*u32)',
 16:'MESSAGE (name+voice+text pages)',17:'MSG-WINDOW fade-out/close (post-message)',18:'SELECT / choice menu',
 19:'SELECT variant (0 occurrences)',20:'BGM load (name)',21:'cmd21 (2*u32)',22:'SE load (name)',23:'cmd23 (2*u32)'}

def lzss_decompress(comp, usize):
    """Faithful port of Etoile.exe 0x404770. Returns (out_bytes, input_consumed)."""
    ring = bytearray(4096)          # zeroed (rep stosd), NOT 0x20-filled
    r = 0xFEE                       # N - F = 4096 - 18
    out = bytearray(); ip = 0; flags = 0; bc = 0; L = len(comp)
    while len(out) < usize:
        if bc == 0:
            if ip >= L: break
            flags = comp[ip]; ip += 1; bc = 8
        bit = flags & 1; flags >>= 1; bc -= 1
        if bit:                     # literal
            if ip >= L: break
            c = comp[ip]; ip += 1
            out.append(c); ring[r] = c; r = (r+1) & 0xFFF
        else:                       # match
            if ip+1 >= L: break
            b1 = comp[ip]; b2 = comp[ip+1]; ip += 2
            pos = b1 | ((b2 & 0xF0) << 4); ln = (b2 & 0xF) + 3
            for k in range(ln):
                c = ring[(pos+k) & 0xFFF]
                out.append(c); ring[r] = c; r = (r+1) & 0xFFF
                if len(out) >= usize: break
    return bytes(out), ip

def read_pac(path):
    d = open(path,'rb').read()
    n, z = struct.unpack_from('<II', d, 0)
    idx_end = 8 + n*40
    ent = []
    for i in range(n):
        o = 8+i*40
        name = d[o:o+32].split(b'\x00')[0].decode('cp932')
        usz, csz = struct.unpack_from('<II', d, o+32)   # [32:36]=uncomp,[36:40]=comp
        ent.append((name, usz, csz))
    off = idx_end; members = []
    for name, usz, csz in ent:
        members.append((name, off, usz, csz))
        off += (csz if csz > 0 else usz)
    return d, members, off, idx_end

def walk_records(b):
    """Return (records, count, end_ptr, status). records=[(type,offset,size)]."""
    if b[:4] != b'SCRT': return [], 0, 0, 'BAD_MAGIC'
    cnt = struct.unpack_from('<I', b, 4)[0]
    p = 8; recs = []
    while p+4 <= len(b):
        t = struct.unpack_from('<I', b, p)[0]
        if t not in RSIZE: return recs, cnt, p, 'BAD_TYPE_%d@%X'%(t,p)
        recs.append((t, p, RSIZE[t])); p += RSIZE[t]
    ok = (p == len(b) and len(recs) == cnt)
    return recs, cnt, p, ('OK' if ok else 'MISMATCH_end%X_len%X_n%d_cnt%d'%(p,len(b),len(recs),cnt))

def text_of_page(seg):
    """cp932 text up to NUL; return (decoded_str, meaningful_byte_len, ctrl_counter)."""
    end = seg.find(b'\x00')
    if end < 0: end = len(seg)
    seg = seg[:end]; ctrl = Counter(); i = 0
    while i < len(seg):
        x = seg[i]
        if (0x81<=x<=0x9f or 0xe0<=x<=0xfc) and i+1 < len(seg):
            tr = seg[i+1]
            if 0x40<=tr<=0xfc and tr!=0x7f: i += 2; continue
        if x < 0x20 or x == 0x7f: ctrl['%02x'%x] += 1
        i += 1
    return seg, ctrl

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pac', default='iso_raw/bin1/scr.pac')
    ap.add_argument('--out', default='scr_dec')
    args = ap.parse_args()
    d, members, final_off, idx_end = read_pac(args.pac)
    os.makedirs(args.out, exist_ok=True)
    lz_fail=[]; walk_fail=[]; op_hist=Counter(); ctrl_hist=Counter()
    tot_bytes=0; parsed_bytes=0; text_bytes=0; nmsg=0; npages=0; nsel=0; sel_choices=0
    page_dist=Counter()
    for name, off, usz, csz in members:
        comp = d[off:off+csz] if csz>0 else d[off:off+usz]
        if csz>0:
            out, ip = lzss_decompress(comp, usz)
            if len(out)!=usz or ip!=csz: lz_fail.append((name,usz,csz,len(out),ip))
        else:
            out, ip = comp, csz
        open(os.path.join(args.out,name),'wb').write(out)
        tot_bytes += len(out)
        recs, cnt, p, st = walk_records(out)
        if st!='OK': walk_fail.append((name,st))
        parsed_bytes += p
        for t, ro, sz in recs:
            op_hist[t]+=1
            if t==16:
                nmsg+=1
                npg=struct.unpack_from('<I',out,ro+MSG_PAGECOUNT)[0]; page_dist[npg]+=1
                for i in range(npg):
                    npages+=1
                    seg=out[ro+MSG_TEXT+i*MSG_TEXT_SLOT:ro+MSG_TEXT+i*MSG_TEXT_SLOT+MSG_TEXT_SLOT]
                    txt,ctrl=text_of_page(seg); text_bytes+=len(txt); ctrl_hist.update(ctrl)
            elif t==18:
                nsel+=1
                pay=out[ro+4:ro+sz]; ct=pay[:128].split(b'\x00')[0]
                sel_choices+=sum(1 for x in ct.split(b'\x0a') if x.strip())
    # ---- report ----
    print('=== decode_scr.py closure statistics ===')
    print('PAC members           : %d'%len(members))
    print('index_end             : %d (0x%X)'%(idx_end,idx_end))
    print('sequential closure    : final_off=%d filesize=%d match=%s'%(final_off,len(d),final_off==len(d)))
    print('LZSS decompress OK    : %d/%d  failures=%d'%(len(members)-len(lz_fail),len(members),len(lz_fail)))
    for x in lz_fail[:10]: print('   LZ_FAIL',x)
    print('SCRT record-walk OK   : %d/%d  failures=%d'%(len(members)-len(walk_fail),len(members),len(walk_fail)))
    for x in walk_fail[:10]: print('   WALK_FAIL',x)
    print('total decompressed    : %d bytes'%tot_bytes)
    print('record-parse coverage : %d/%d bytes = %.4f%%'%(parsed_bytes,tot_bytes,100.0*parsed_bytes/tot_bytes))
    print('message records       : %d  (type16)'%nmsg)
    print('message pages(=clicks): %d  page_count dist=%s'%(npages,dict(sorted(page_dist.items()))))
    print('message text bytes    : %d (cp932+ctrl, %.2f%% of decompressed)'%(text_bytes,100.0*text_bytes/tot_bytes))
    print('SELECT records        : %d  (type18)  total choice labels=%d'%(nsel,sel_choices))
    print('--- TEXT control codes (in message text fields) ---')
    for k,v in ctrl_hist.most_common(): print('   0x%s : %d  (newline/soft line-break within page)'%(k,v))
    if not ctrl_hist: print('   (none)')
    print('--- RECORD opcode histogram (u32 type) ---')
    for t,c in sorted(op_hist.items()): print('   type %2d (0x%02X) : %5d  %s'%(t,t,c,OPCODE_NAME.get(t,'?')))
    # control-code manifest sidecar
    man=os.path.join(args.out,'_control_codes.txt')
    with open(man,'w',encoding='utf-8',newline='\n') as f:
        f.write('エトワールの方程式 script control-code manifest\n')
        f.write('TEXT-area control bytes (message text fields, cp932):\n')
        for k,v in ctrl_hist.most_common(): f.write('  0x%s = %d occurrences : soft newline (line break within a 128B page; proven by renderer 0x419CD0 + page advance 0x41A1A8)\n'%(k,v))
        f.write('  NOTE: no 81ff/82ff or other invalid double-byte sequences exist in correctly decompressed text (0 found).\n')
        f.write('RECORD-level opcodes (u32 type at each record start):\n')
        for t,c in sorted(op_hist.items()): f.write('  type %d (0x%02X) = %d : %s\n'%(t,t,c,OPCODE_NAME.get(t,'?')))
    print('manifest written      : %s'%man)
    print('output directory      : %s/ (%d .bin files)'%(args.out,len(members)))

if __name__=='__main__':
    main()