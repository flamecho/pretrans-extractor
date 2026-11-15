# -*- coding: utf-8 -*-
"""dump raw bytes around a literal hit in a .spt (XOR 0xFF decoded)."""
import sys, os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SPT = os.path.join(VNTRANS_HOME, '_work_koutari/iso/app/spt')
def decrypt(p): return bytes(b ^ 0xFF for b in open(p,'rb').read())

# 在指定文件里找 needle（cp932 串）并打印前后字节
needle = sys.argv[1].encode('cp932') if len(sys.argv)>2 else '#名'.encode('cp932')
fn = os.path.join(SPT, sys.argv[2]) if len(sys.argv)>2 else os.path.join(SPT,'Midori_route2.spt')
n = decrypt(fn)
idx = n.find(needle)
print("file:", os.path.basename(fn), "len:", len(n), "hit@", idx)
if idx<0:
    print("no hit"); sys.exit()
lo = max(0, idx-40); hi = min(len(n), idx+len(needle)+60)
seg = n[lo:hi]
print("hex:", seg.hex())
# 逐字节标注 cp932 可解部分
i=0
out=[]
while i < len(seg):
    b=seg[i]
    if 0x20<=b<=0x7e:
        out.append(('.%c'%b, b))
    elif b==0:
        out.append(('<NUL>',0))
    elif b in (0x0d,0x0a):
        out.append(('<CR>' if b==0x0d else '<LF>',b))
    elif (0x81<=b<=0x9f) or (0xe0<=b<=0xfc):
        if i+1<len(seg):
            try: ch=seg[i:i+2].decode('cp932'); out.append((ch,seg[i+1])); i+=1
            except: out.append(('[%02x]'%b,b))
        else: out.append(('[%02x]'%b,b))
    elif 0xa1<=b<=0xdf:
        try: ch=seg[i:i+1].decode('cp932'); out.append((ch,b))
        except: out.append(('[%02x]'%b,b))
    else:
        out.append(('[%02x]'%b,b))
    i+=1
print("annot:", ' '.join('%s'%a for a,b in out))
