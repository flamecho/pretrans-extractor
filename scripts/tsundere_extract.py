#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ツンデレ★Ｓ乙女 (PC / 美蕾「Madoka GScript」) 全文本提取器 —— 本项目定稿
用法: python tsundere_extract.py <ツンデレ★Ｓ乙女.sce> <out.txt>
说明见本作品解析报告
"""
import sys, re, os
import numpy as np

MUL=0x41C64E6D; ADD=0x3039; SEED=0x915354A9; MASK=0xFFFFFFFF
def lcg_table():
    t=[]; s=SEED
    for _ in range(256):
        t.append(s); s=(s*MUL+ADD)&MASK
    return b''.join(int(x).to_bytes(4,'little') for x in t)
TB=lcg_table()
ORDER=[(0x43+0x17*(i-1))&0x3ff for i in range(1,1024)]     # stride-23 scatter

def decrypt_block(raw):
    """fillB(0x44c7bb) 0x30001 路径: chain(un-scatter+prefix-XOR) → 256×dword 表异或。seed=0 基准。"""
    w=bytearray(1024); pref=0
    for i,idx in enumerate(ORDER,1):
        pref^=raw[idx]; w[i]=pref^TB[i]
    w[0]=TB[0]
    return w

# ---- 逐块 seed 复原（评分：日文标点/假名/汉字 − 单字节主导惩罚）----
S1=[0x41,0x42,0x75,0x76,0x40,0x63,0x5e,0x9f,0x48,0x49]
_sds=np.arange(256,dtype=np.int32)
_r81=(0x81^_sds); _r82=(0x82^_sds)
_lead=np.array([v for v in range(0x88,0xA0)]+[v for v in range(0xE0,0xEB)],dtype=np.int32)
def score_block(blk):
    pair=(blk[:-1].astype(np.int32)<<8)|blk[1:].astype(np.int32)
    H=np.bincount(pair,minlength=65536).reshape(256,256)
    BH=np.bincount(blk,minlength=256).astype(np.float64)
    pun=np.zeros(256,np.int32)
    for s in S1: pun+=H[_r81,(_sds^s)]
    hira=np.zeros(256,np.int32)
    for t in range(0xA0,0xF2): hira+=H[_r82,(_sds^t)]
    kanji=BH[_lead^_sds[:,None]].sum(axis=1)
    topfrac=BH[_sds[:,None]^np.arange(256)].max(axis=1)/1024.0
    sc=8*pun+2*hira+0.5*kanji-np.where(topfrac>0.30,800,0)
    k=int(sc.argmax())
    return k,int(sc[k])

NAME1=b'\x05\x80\x80\x80\xd3\xbf'   # 姓 → 月城
NAME2=b'\x05\x80\x80\x80\xd3\xc0'   # 名 → いおり
def clean(s):
    s=s.replace(NAME1,'月城'.encode('cp932')).replace(NAME2,'いおり'.encode('cp932'))
    try: t=s.decode('cp932')
    except: return None
    # 注音 \x10 base \x11 reading \x12 → base
    t=re.sub(r'\x10(.*?)\x11.*?\x12',r'\1',t)
    # 框内换行合并
    t=t.replace('\x08','')
    # 残留控制码
    t=re.sub(r'[\x00-\x1f]','',t)
    return t

def extract(path,out):
    data=open(path,'rb').read()
    assert data[:4]==b'CRPT'
    pay=data[0x20:]
    NB=len(pay)//0x400
    blocks=np.frombuffer(pay[:NB*0x400],dtype=np.uint8).reshape(NB,0x400)
    # 先把「文本块」（含相邻 ±1 块，防止跨块字符串被截断）解密并拼接，再按 \0 切分
    keep=np.zeros(NB,dtype=bool); dec=[None]*NB
    for bi in range(NB):
        base=decrypt_block(bytes(blocks[bi]))
        k,sc=score_block(np.frombuffer(base,dtype=np.uint8))
        dec[bi]=(k,sc,bytes(c^k for c in base))
        if sc>=150: keep[bi]=True
    for bi in range(NB):
        if keep[bi]:
            for j in (bi-1,bi+1):
                if 0<=j<NB: keep[j]=True
    stream=bytearray()
    for bi in range(NB):
        if keep[bi]: stream+=dec[bi][2]
    lines=[]; ctrl=set()
    for s in bytes(stream).split(b'\x00'):
        if len(s)<2: continue
        t=clean(s)
        if t is None: continue
        j=sum(1 for ch in t if 0x3040<=ord(ch)<=0x9fff or ch in '、。「」『』…―')
        if j<1 or j<len(t)*0.4: continue
        for ch in t:
            if ord(ch)<0x20: ctrl.add(hex(ord(ch)))
        lines.append(t)
    with open(out,'w',encoding='utf-8-sig',newline='\n') as f:
        f.write('\n'.join(lines)+'\n')
    print("blocks:",NB,"lines:",len(lines),"chars:",sum(len(l) for l in lines),"leftover ctrl:",ctrl)

if __name__=='__main__':
    extract(sys.argv[1], sys.argv[2])
