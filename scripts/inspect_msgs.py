# -*- coding: utf-8 -*-
"""列出某 .spt 中以 \0 分隔的消息序列（解码 + 字节），用于肉眼确认格式。"""
import os, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SPT = os.path.join(VNTRANS_HOME, '_work_koutari/iso/app/spt')
def decrypt(p): return bytes(b ^ 0xFF for b in open(p,'rb').read())

fn = os.path.join(SPT, sys.argv[1] if len(sys.argv)>1 else 'status.spt')
n = decrypt(fn)
# 找 pool 起点（SPTHEADER0 + 0x60 后第一个 >=8 字节的 cp932 串）
def is_lead(b): return (0x81<=b<=0x9f) or (0xe0<=b<=0xfc)
def cplen(i,L):
    j=i
    while j<L:
        c=n[j]
        if c==0: break
        if is_lead(c):
            if j+1<L and ((0x40<=n[j+1]<=0x7e) or (0x80<=n[j+1]<=0xfc)): j+=2
            else: return -1
        elif 0x20<=c<=0x7e or 0xa1<=c<=0xdf or c in (0x0d,0x0a,0x09): j+=1
        else: return -1
    return j-i
hdr=n.find(b'SPTHEADER0'); start=hdr+0x60 if hdr>=0 else 0x100
pool=None
for i in range(start,len(n)-8):
    if cplen(i,len(n))>=8: pool=i; break
# 从 pool 起，逐条 \0 分隔
L=len(n); i=pool; seq=[]
cur=[]
while i<L and len(seq)<200:
    b=n[i]
    if b==0:
        if cur: seq.append(bytes(cur)); cur=[]
        i+=1; continue
    cur.append(b); i+=1
    if i-pool>40000: break
# 解码每条（遇解码错用 . 替）
out=[]
for raw in seq:
    try: t=raw.decode('cp932')
    except: t=raw.decode('cp932','replace')
    out.append((raw.hex(), t))
print("file:", os.path.basename(fn), "pool@", pool, "msg count shown:", len(out))
for k,(hx,t) in enumerate(out[:120]):
    # 限制显示长度
    disp = t if len(t)<=70 else t[:70]+'…'
    print(f"[{k:3}] {hx[:24]:24} | {disp!r}")
