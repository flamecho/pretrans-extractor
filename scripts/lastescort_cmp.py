# -*- coding: utf-8 -*-
"""对比 深夜の黒蝶物語（本编）与 黒蝶スペシャルナイト（追加碟）的 ADV.FPK / VML

前提：两盘 DATA/ADV.FPK 已解到 _src_lescortps2/ 与 _src_kurocho/（见重合对照报告 §5）。
注意：字节层 831/831 全不同（重编译），判重只能按 0x68 文本载荷。
"""
import struct, hashlib, collections
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())


def read_fpk(path):
    d = open(path, 'rb').read()
    cnt, = struct.unpack('<I', d[:4])
    ent = {}
    for i in range(cnt):
        o = 0x20 + i * 32
        nm = d[o:o + 16].rstrip(b'\0').decode('latin1')
        sz, off = struct.unpack('<II', d[o + 16:o + 24])
        ent[nm] = d[off:off + sz]
    return d, ent


A = os.path.join(VNTRANS_HOME, '_src_lescortps2/ADV.FPK')   # 深夜の黒蝶物語
B = os.path.join(VNTRANS_HOME, '_src_kurocho/ADV.FPK')      # 黒蝶スペシャルナイト
da, ea = read_fpk(A)
db, eb = read_fpk(B)
print('本编 entries', len(ea), '追加碟 entries', len(eb))

va = {k: v for k, v in ea.items() if k.endswith('.VML')}
vb = {k: v for k, v in eb.items() if k.endswith('.VML')}
print('本编 VML', len(va), '追加碟 VML', len(vb))

ha = {k: hashlib.md5(v).hexdigest() for k, v in va.items()}
hb = {k: hashlib.md5(v).hexdigest() for k, v in vb.items()}

same = [k for k in ha if k in hb and ha[k] == hb[k]]
diff = [k for k in ha if k in hb and ha[k] != hb[k]]
onlyA = [k for k in ha if k not in hb]
onlyB = [k for k in hb if k not in ha]
print('同名且字节完全相同', len(same))
print('同名但内容不同', len(diff), diff[:10])
print('仅本编有', len(onlyA), sorted(onlyA)[:20])
print('仅追加碟有', len(onlyB), sorted(onlyB)[:30])

# 名札/正文记录数对比（同名字节相同则必然一致）
def stats(b):
    n68 = n64 = nf6 = 0
    i = 0
    while True:
        j = b.find(b'\x00\xff', i)
        if j < 0 or j < 2:
            break
        op = b[j - 2] | (b[j - 1] << 8)
        if op == 0x68:
            n68 += 1
        elif op == 0x64:
            n64 += 1
        elif op == 0x1F6:
            nf6 += 1
        i = j + 2
    return n68, n64, nf6


ta = [0, 0, 0]
for k in same:
    s = stats(va[k])
    for i in range(3):
        ta[i] += s[i]
print('完全相同的那批（本编字节口径）记录数 68/64/F6 =', ta)
