# -*- coding: utf-8 -*-
# 本作真实加密模型：文件按 0x400(1024) 字节分块，每块用一把独立单字节 XOR 密钥。
# 逐块定钥：先用字节级打分选 top3，再用字符级打分确认。
data=open('gsce_decrypted.bin','rb').read()
T=[bytes([b^k for b in range(256)]) for k in range(256)]
# 字节级权重（针对 (b^k) 得到的明文字节）
W=[0]*256
for b in range(256):
    if 0x81<=b<=0x9f or 0xe0<=b<=0xfc: W[b]=3      # cp932 前导字节
    elif 0x40<=b<=0x7e or 0x80<=b<=0xfc: W[b]=1     # 尾字节/ASCII
    elif b==0: W[b]=2                               # 分隔符
    elif 0x20<=b<=0x3f: W[b]=0
    elif b==0xff or b==0xa0: W[b]=-4
    elif 0xa1<=b<=0xdf: W[b]=-4                     # 半角假名＝控制码
    else: W[b]=-1
WT={k:bytes((W[b^k]+8)&0xff for b in range(256)) for k in range(256)}
def char_score(blk,k):
    s=bytes(b^k for b in blk).decode('cp932','replace'); sc=0
    for c in s:
        o=ord(c)
        if 0x3040<=o<=0x30ff: sc+=3
        elif 0x4e00<=o<=0x9fff: sc+=2
        elif c in '、。！？…「」ー（）・': sc+=2
        elif o==0xfffd: sc-=4
        elif 0xff61<=o<=0xff9f: sc-=4
        elif 0xe000<=o<=0xf8ff: sc-=4
    return sc
BS=0x400
out=bytearray(); keys=[]
n=len(data)
for base in range(0,n,BS):
    blk=data[base:base+BS]
    cand=[];
    for k in range(256):
        cand.append((sum(blk.translate(WT[k]))-8*len(blk),k))
    cand.sort(reverse=True)
    best=None
    for _,k in cand[:3]:
        v=char_score(blk,k)
        if best is None or v>best[0]: best=(v,k)
    k=best[1]; keys.append(k)
    out+=bytes(b^k for b in blk)
open('plain.bin','wb').write(bytes(out))
print('块数',len(keys),'长度',len(out))
from collections import Counter
print('密钥分布 top',[( '%02x'%a,b) for a,b in Counter(keys).most_common(8)])
s=out.decode('cp932','replace')
for t in ('クラスメイトの原田奈緒','泥だんご事件','忘れたい過去','皆さん、おはようございます'):
    i=s.find(t); print('%-14s %s'%(t,hex(i) if i>=0 else '未找到'))
