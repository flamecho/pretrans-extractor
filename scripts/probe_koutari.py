# -*- coding: utf-8 -*-
"""koutari 侦查：罗列两类可疑行的证据（源文件 + 原始字节）。"""
import os, re, glob, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SPT_DIR = os.path.join(VNTRANS_HOME, '_work_koutari/iso/app/spt')

def decrypt(p):
    return bytes(b ^ 0xFF for b in open(p, 'rb').read())

def is_lead(b):
    return (0x81 <= b <= 0x9f) or (0xe0 <= b <= 0xfc)

def cp932_len(n, i, L):
    j = i
    while j < L:
        c = n[j]
        if c == 0:
            break
        if is_lead(c):
            if j + 1 < L and ((0x40 <= n[j+1] <= 0x7e) or (0x80 <= n[j+1] <= 0xfc)):
                j += 2
            else:
                return -1
        elif 0x20 <= c <= 0x7e or 0xa1 <= c <= 0xdf or c in (0x0d,0x0a,0x09):
            j += 1
        else:
            return -1
    return j - i

def walk(n, start):
    L=len(n); out=[]; i=start; last=start
    while i < L:
        ln = cp932_len(n, i, L)
        if ln >= 1:
            try: t = n[i:i+ln].decode('cp932')
            except: t = None
            if t is not None:
                out.append((t, i)); i = i+ln+1; last=i; continue
        if i-last > 256: break
        i += 1
    return out

HW = lambda ch: 0xFF61 <= ord(ch) <= 0xFF9F  # 半角カナ（解码后）

def garble_token(t):
    """取开头连续『半角カナ / 小写ascii / 数字』作为乱码标记；遇日文或引号即止。"""
    j=0
    while j < len(t):
        ch=t[j]
        if HW(ch) or (ch.isascii() and (ch.islower() or ch.isdigit())):
            j+=1
        else:
            break
    return t[:j] if j>0 else None

files = sorted(glob.glob(os.path.join(SPT_DIR, '*.spt')))
ascii_hits = []
hwk = collections.defaultdict(lambda:[0,'','',set()])
for f in files:
    n = decrypt(f); L=len(n)
    hdr = n.find(b'SPTHEADER0')
    start = hdr + 0x60 if hdr>=0 else 0x100
    pool=None
    for i in range(start, L-8):
        if cp932_len(n,i,L)>=8: pool=i; break
    if pool is None: continue
    for t, off in walk(n, pool):
        if not t: continue
        c0=t[0]
        if c0.isascii() and c0.isalpha():
            ascii_hits.append((t, os.path.basename(f), off))
        elif HW(c0):
            tok = garble_token(t)
            if not tok: continue
            rec = hwk[tok]
            rec[0]+=1
            if not rec[1]:
                rec[1]=t[len(tok):][:30]; rec[2]=n[off:off+min(14,len(t.encode('cp932','ignore'))*2)].hex()
            rec[3].add(os.path.basename(f))

print("=== ASCII-tag leads: %d (unique %d) ===" % (len(ascii_hits), len(set(ascii_hits))))
for t,f,off in sorted(set(ascii_hits)):
    print(f"  [{f}] {t[:46]}")
print()
print("=== half-width-kana garble tokens: %d unique, %d total ===" % (
    len(hwk), sum(v[0] for v in hwk.values())))
for tok,(cnt,sb,hx,fls) in sorted(hwk.items(), key=lambda x:-x[1][0])[:40]:
    print(f"  x{cnt:4} tok={tok!r} hex={hx} body={sb!r} f={sorted(fls)[:2]}")
