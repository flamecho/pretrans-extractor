# -*- coding: utf-8 -*-
# [JP]S-Tripper（Monoceros STMD/STSL）提取器。
# 用法: python stripper_extract.py <ST_MSG.DAT> <ST_SNR.DAT> [输出.txt]
#   无 argv 时用默认 _work_stripper 路径（仅供原工作目录在时复核）；
#   输出默认锚定 <_Trans>/提取结果/[JP]S-Tripper.txt。
# 重跑：先用 scripts/ccdimg.py 从母本 CloneCD 镜像解出 ST_MSG.DAT/ST_SNR.DAT，再传路径给本工具。
import struct, re, collections, sys, os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
if len(sys.argv) >= 3:
    MSG, SNR = sys.argv[1], sys.argv[2]
else:
    MSG = os.path.join(VNTRANS_HOME, '_work_stripper/disk1/SETUPD~1/DATA/ST_MSG.DAT')
    SNR = os.path.join(VNTRANS_HOME, '_work_stripper/disk1/SETUPD~1/DATA/ST_SNR.DAT')
OUT = sys.argv[3] if len(sys.argv) >= 4 else os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '提取结果', '[JP]S-Tripper.txt')
b = open(MSG,'rb').read()
count = struct.unpack_from('<I', b, 6)[0]
pool = struct.unpack_from('<I', b, 10)[0]
ds = len(b)-pool
recs=[]; pos=ds
for i in range(count):
    ln=struct.unpack_from('<I',b,pos)[0]
    recs.append(bytes(x^0xFF for x in b[pos+4:pos+4+ln]).decode('cp932'))
    pos+=4+ln
BS=chr(0x5c)
VOICE=re.compile(re.escape(BS)+r'v[^;]*;')
def term(t):
    for tag in (BS+'n',BS+'k',BS+'K'):
        if t.endswith(tag): return tag
    return None
def clean(t):
    s=VOICE.sub('',t)
    for tag in (BS+'n',BS+'k',BS+'K'):
        if s.endswith(tag): s=s[:-2]; break
    s=s.replace(BS+'k','').replace(BS+'K','').replace(BS+'n','').replace(BS+'c','')
    return s
EXCLUDE={8736,8737,8738,8739}
# scan scenario events
s=open(SNR,'rb').read(); n=len(s)
events=[]  # (offset, kind, payload)
i=0
while i<n-5:
    if s[i]==0x00 and s[i+1]==0x80:
        idx=struct.unpack_from('<I',s,i+2)[0]
        if idx<count:
            events.append((i,'msg',idx)); i+=6; continue
    if s[i]==0x28 and s[i+1]==0x00 and s[i+2]==0x01 and i+5<=n:
        ln=struct.unpack_from('<H',s,i+3)[0]
        if 0<ln<400 and i+5+ln<=n:
            try:
                t=s[i+5:i+5+ln].decode('cp932')
                if all(ord(c)>=0x20 for c in t):
                    events.append((i,'opt',t)); i+=5+ln; continue
            except: pass
    i+=1
events.sort(key=lambda e:e[0])
msgc=sum(1 for e in events if e[1]=='msg')
optc=sum(1 for e in events if e[1]=='opt')
print('events: msg',msgc,'opt',optc,'total',len(events))
# walk events, build pages + options in order
lines=[]
cur=[]
dual_pages=0; single_pages=0; seg_total=0; opt_total=0; empty_skip=0
def emit_chain(c):
    global dual_pages,single_pages,seg_total,empty_skip
    disp=[]; merge=[]
    for j,i in enumerate(c):
        t=clean(recs[i])
        if j>0: t=t.lstrip(' \u3000')   # strip continuation alignment indent
        d=t.rstrip(' \u3000')           # 段行：clean standalone line
        if d.strip(' \u3000')=='':
            empty_skip+=1; continue
        m=t.rstrip('\u3000')            # 整页行：keep trailing halfwidth space (English word sep), drop fullwidth layout pad
        disp.append(d); merge.append(m)
    if not disp: return
    if len(disp)==1:
        lines.append(disp[0]); single_pages+=1; seg_total+=1
    else:
        dual_pages+=1
        for t in disp: lines.append(t); seg_total+=1
        lines.append(''.join(merge).rstrip(' \u3000'))
for off,kind,pl in events:
    if kind=='opt':
        if cur: emit_chain(cur); cur=[]
        lines.append(pl); opt_total+=1
    else:
        idx=pl
        if idx in EXCLUDE:
            if cur: emit_chain(cur); cur=[]
            continue
        tm=term(recs[idx])
        if tm is None:
            if cur: emit_chain(cur); cur=[]
            emit_chain([idx])
            continue
        cur.append(idx)
        if tm in (BS+'k',BS+'K'):
            emit_chain(cur); cur=[]
if cur: emit_chain(cur)
print('pages: single',single_pages,'dual',dual_pages,'segments',seg_total,'options',opt_total,'empty_skip',empty_skip)
print('total lines',len(lines))
# closure: segments + dual whole-page lines + options = total
print('closure check:', seg_total+dual_pages+opt_total, '==', len(lines))
# write deliverable: UTF-8 BOM + LF
data='\n'.join(lines)+'\n'
with open(OUT,'wb') as f:
    f.write(b'\xef\xbb\xbf'+data.encode('utf-8'))
print('written', OUT)
# stats for report
print('CR count', data.count('\r'), 'FFFD', data.count('\ufffd'), 'control', sum(1 for c in data if ord(c)<0x20 and c!='\n'))