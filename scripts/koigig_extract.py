# -*- coding: utf-8 -*-
"""
KoiGIG ～DEVIL×ANGEL～ (TWOFIVE / DonMaccow, 2007) 文本提取器
引擎: MNP (GameRes.Formats.Mnp)  — 归档 ARC!/MMA，加密+自定义 LZ
剧本: data34.mma 内 sn_* (MNP 脚本，cp932)
UI/系统: data35.mma 内 *_mode / SystemInfo
规范: 一次点击 = 一行；行内换行合并；保留日文；不加说话人前缀；主角名 inline
"""
import os, re, sys, struct

# ---------- MNP / MMA 解码 ----------
KEY = bytes([
 0x77,0x2C,0x6F,0x7A,0x71,0x4F,0x25,0x74,0x6C,0x28,0x7A,0x81,0x4C,0x31,0x81,0x5B,
 0x77,0x81,0x4D,0x79,0x29,0x69,0x45,0x6B,0x79,0x7A,0x68,0x2D,0x69,0x66,0x29,0x39])
def _rotl(x,n): return ((x<<n)|(x>>(8-n)))&0xFF
def _rotr(x,n): return ((x>>n)|(x<<(8-n)))&0xFF
_TAB_ROR3=bytes(_rotr(i,3) for i in range(256))
_TAB_ROL5=bytes(_rotl(i,5) for i in range(256))

def _xor_key(block):
    k=len(KEY)
    key=(KEY*(len(block)//k+1))[:len(block)]
    return (int.from_bytes(block,'big')^int.from_bytes(key,'big')).to_bytes(len(block),'big')

def decrypt(block):
    return _xor_key(block).translate(_TAB_ROR3)

def unpack_lz(data, out_size):
    e=bytearray(_xor_key(data))
    if e[0]==0xC0: src=e; p=1
    elif data[0]==0xC0: src=bytearray(data); p=1
    elif data[0]==0x00: return bytes(data[:out_size])
    else: raise ValueError('bad LZ id 0x%02x'%data[0])
    out=bytearray(); ctl=0; mask=0; pos=p
    while len(out)<out_size:
        if mask==0:
            if pos>=len(src): break
            ctl=src[pos]; pos+=1; mask=0x80
        if ctl & mask:
            off=(src[pos]<<8)|src[pos+1]; pos+=2
            count=(off&0x1F)+3; off=(off>>5)+1
            st=len(out)-off
            if count<=off: out+=out[st:st+count]
            else:
                for _ in range(count): out.append(out[st]); st+=1
        else:
            out.append(_TAB_ROL5[src[pos]]); pos+=1
        mask>>=1
    return bytes(out)

def parse_arc(path):
    d=open(path,'rb').read()
    assert d[:4]==b'ARC!', path
    idx=struct.unpack('<I',d[4:8])[0]
    cnt=struct.unpack('<I',d[0x10:0x14])[0]
    ents=[]
    for i in range(cnt):
        o=idx+i*0x14
        off,us,cs,hdr,fl=struct.unpack('<5I',d[o:o+0x14])
        ents.append(dict(off=off,us=us,cs=cs,hdr=hdr,flags=fl))
    return d,ents

def unpack_entry(d,e):
    fl=e['flags']&6
    raw=d[e['off']:e['off']+e['cs']]
    if fl==6 and e['hdr']==0: return unpack_lz(raw,e['us'])
    elif fl==4:
        return decrypt(d[e['off']+e['hdr']: e['off']+e['hdr']+e['us']])
    return raw

def archive_names(d,ents):
    if ents and ents[0]['flags']==0x2f:
        return unpack_entry(d,ents[0]).decode('cp932').replace('\r\n','\n').split('\n')
    return []

# ---------- 文本清洗 ----------
NAME_MAP={'name1':'柊木','name2':'法子','name3':'ノリ','name4':'シュウ・ミック・ノリ','name5':'賢さん・法子'}
def clean(s):
    s=re.sub(r'\\v\([^)]*\)','',s)       # 声優/ボイスID
    s=re.sub(r'\\c\([^)]*\)','',s)       # 話者ID（ネームプレート）
    s=re.sub(r'\\np\([^)]*\)','',s)      # ネームプレート番号
    s=re.sub(r'\\nowait','',s)
    s=re.sub(r'\\w','',s)
    s=re.sub(r'\\var\(([^)]*)\)', lambda m: NAME_MAP.get(m.group(1), m.group(1)), s)
    s=s.replace('\\n','')                 # 框内换行→合并
    return s.strip(' \u3000')

def quoted(rest):
    i=rest.find('"')
    if i<0: return None
    j=rest.rfind('"')
    if j<=i: return None
    return rest[i+1:j]

TEXT_CMDS=('put','item','site','nameinput')

def scan_text(decoded, out):
    """线性扫描剧本文本，put/item/site/nameinput 各输出一行；支持 'lb_xx:cmd' 行首标签"""
    for line in decoded.replace('\r\n','\n').split('\n'):
        if not line: continue
        head,_,rest = line.partition('\t')
        cmd = head.rsplit(':',1)[-1]                 # 去掉 lb_02: 之类标签前缀
        if cmd in TEXT_CMDS:
            t=quoted(rest if rest else line[len(head):])
            if t is not None:
                t=clean(t)
                if t: out.append(t)

# ---------- 主流程 ----------
def main(src, dst):
    d,ents=parse_arc(os.path.join(src,'data34.mma'))
    names=archive_names(d,ents)
    files={}
    for i,e in enumerate(ents):
        nm=names[i] if i<len(names) and names[i] else 'sn_%04d'%i
        files[nm]=unpack_entry(d,e)

    # 顺序：共通 → シュウ編 → トラ編 → ラン編 → ミック編 → おまけ
    def block(prefix, idxs, withbad=True):
        res=[]
        for n in idxs:
            res.append(n)
            b=n+'bad'
            if withbad and b in files: res.append(b)
        return res
    order=[]
    order.append(('■ 共通ルート', ['sn_00','sn_01','sn_01bad','sn_02','sn_03','sn_03bad','sn_04','sn_05',
                                   'sn_11','sn_12','sn_21','sn_22']))
    order.append(('■ シュウ編', block('shu',['sn_shu_%02d'%i for i in range(1,20)])))
    order.append(('■ トラ編', block('tra',['sn_tra_%02d'%i for i in range(1,21)])))
    order.append(('■ ラン編', block('run',['sn_run_%02d'%i for i in range(1,19)])))
    order.append(('■ ミック編', block('mic',['sn_mic_%02d'%i for i in range(1,20)])))
    order.append(('■ おまけシナリオ', ['sn_99']))

    lines=[]; stats=[]
    for title, fl in order:
        if lines: lines.append('')
        lines.append(title)
        cnt0=len(lines)
        for fn in fl:
            if fn not in files:
                print('  [warn] missing', fn); continue
            tmp=[]
            scan_text(files[fn].decode('cp932','replace'), tmp)
            lines.extend(tmp)
            stats.append((fn,len(tmp)))
        print('%-16s lines=%d'%(title,len(lines)-cnt0))

    # ---- 系统 / UI 文本 ----
    d35,e35=parse_arc(os.path.join(src,'data35.mma'))
    n35=archive_names(d35,e35)
    f35={}
    for i,e in enumerate(e35):
        nm=n35[i] if i<len(n35) and n35[i] else 'f_%04d'%i
        f35[nm]=unpack_entry(d35,e).decode('cp932','replace')

    sys_msgs=[]; sys_names=[]
    # 名札テーブル（SystemInfo [Nameplate] item:N=…）★ = 変数プレースホルダ（非表示）
    si=f35.get('SystemInfo','')
    for m in re.finditer(r'^item:(\d+)=(.*)$', si, re.M):
        v=m.group(2).strip().replace('★','')
        if v: sys_names.append(v)
    # クエリ／警告メッセージ
    for fn in ['saveload_mode','game_mode']:
        for m in re.finditer(r'^(?:QuerySaveMessage|QueryLoadMessage|SaveMenuAlarmMessage)=(.*)$', f35.get(fn,''), re.M):
            v=m.group(1).strip()
            if v: sys_msgs.append(v)

    out=list(lines)
    out.append('')
    out.append('■ システム／UI テキスト')
    out.append('［メッセージ］')
    out.extend(sys_msgs)
    out.append('［名札（ネームプレート）］')
    out.extend(sys_names)

    text='\n'.join(out).rstrip('\n')+'\n'
    with open(dst,'w',encoding='utf-8-sig',newline='\n') as fp:
        fp.write(text)
    print('TOTAL lines =', len(out))
    return stats

if __name__=='__main__':
    home=os.environ.get('VNTRANS_HOME', os.getcwd())
    src=sys.argv[1] if len(sys.argv)>1 else os.path.join(home, '_work/koigig/iso/Setup/Disc1')
    dst=sys.argv[2] if len(sys.argv)>2 else os.path.join(home, '_work/koigig/out.txt')
    main(src,dst)
