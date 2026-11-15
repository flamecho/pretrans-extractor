# -*- coding: utf-8 -*-
# v10：直接在 fully-decrypted plain.bin 上提取（分块加密已由 decrypt_blocks.py 解决）
#   结构：脚本按 \x00 分隔字符串；名宏 = 05 80 80 80 + 2B op（c0fe=姓 春日 / c0ff=名 ひなた）
import re
SRC='plain.bin'
OUT='提取结果/Hoshi no Oujo Hikari no Tsubasa + Koi no Patissier.txt'
data=open(SRC,'rb').read()
NAME_MARK=b'\x05\x80\x80\x80'
OP={'c0fe':'春日','c0ff':'ひなた'}
def repl(tok):
    out=bytearray(); i=0; n=len(tok)
    while i<n:
        if tok[i:i+4]==NAME_MARK and i+6<=n:
            op=tok[i+4:i+6].hex()
            nm=OP.get(op)
            if nm:
                out+=nm.encode('cp932'); i+=6; continue
            i+=6; continue          # 未知 op：整体丢弃，绝不留垃圾
        out.append(tok[i]); i+=1
    return bytes(out)
def jp(c):
    o=ord(c); return 0x3040<=o<=0x30ff or 0x4e00<=o<=0x9fff or c in '、。」「…！？ー♪～（）・，．々〆〇０１２３４５６７８９'
def bad(c):
    o=ord(c)
    return (o==0xfffd) or (0xff61<=o<=0xff9f) or (0xe000<=o<=0xf8ff) or (o<0x20) or (0x7f<=o<0xa0)
def coherent(s):
    if len(s)<2: return False
    if any(bad(c) for c in s): return False
    hira=sum(1 for c in s if 0x3041<=ord(c)<=0x309f)
    if hira<1: return False
    if sum(1 for c in s if jp(c)) < len(s)*0.7: return False
    run=mx=0
    for c in s:
        if 0x4e00<=ord(c)<=0x9fff: run+=1; mx=max(mx,run)
        else: run=0
    if mx>=6 and hira<=1: return False
    return True
lines=[]
for tok in data.split(b'\x00'):
    if len(tok)<3: continue
    if all(0x20<=b<0x7f for b in tok): continue     # 纯 ASCII：label/ID/资源名
    t=repl(tok)
    try: s=t.decode('cp932')
    except Exception: s=t.decode('cp932','replace')
    if coherent(s): lines.append(s.strip('　 '))
print('候选行',len(lines))
open(OUT,'w',encoding='utf-8-sig',newline='\n').write('\n'.join(lines)+'\n')
print('写出',OUT)
