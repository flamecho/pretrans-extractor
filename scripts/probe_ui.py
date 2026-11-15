# -*- coding: utf-8 -*-
"""扫描所有 spt，列出含 UI/菜单关键词的消息（源文件 + 原文）。"""
import os, re, glob
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SPT_DIR = os.path.join(VNTRANS_HOME, '_work_koutari/iso/app/spt')
KEYWORDS = ['タイトル','コンフィグ','ギャラリー','シーン鑑賞','ＢＧＭ','バックログ',
            '称号','ＥＤ・','ルート','セーブ','ロード','ボイス','音量','終了',
            'はい・いいえ','コンテニュー','オート','スキップ','ウィンドウ','メッセージ速度']

def decrypt(p): return bytes(b ^ 0xFF for b in open(p,'rb').read())
def is_lead(b): return (0x81<=b<=0x9f) or (0xe0<=b<=0xfc)
def cplen(n,i,L):
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
def walk(n,start):
    L=len(n); out=[]; i=start; last=start
    while i<L:
        ln=cplen(n,i,L)
        if ln>=1:
            try: t=n[i:i+ln].decode('cp932')
            except: t=None
            if t is not None:
                out.append(t); i=i+ln+1; last=i; continue
        if i-last>256: break
        i+=1
    return out

rx = re.compile('|'.join(re.escape(k) for k in KEYWORDS))
files = sorted(glob.glob(os.path.join(SPT_DIR,'*.spt')))
hits=[]
for f in files:
    n=decrypt(f); L=len(n)
    hdr=n.find(b'SPTHEADER0'); start=hdr+0x60 if hdr>=0 else 0x100
    pool=None
    for i in range(start,L-8):
        if cplen(n,i,L)>=8: pool=i; break
    if pool is None: continue
    for t in walk(n,pool):
        if rx.search(t):
            hits.append((os.path.basename(f), t))
print("UI-keyword hits:", len(hits))
for f,t in hits:
    print(f"  [{f}] {t[:60]!r}")
