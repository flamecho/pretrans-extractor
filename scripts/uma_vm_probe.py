# -*- coding: utf-8 -*-
"""uma_script_2.bytes 结构探针：找「固定步长上的递增 u16/u32」= 文本单位序号序列"""
import struct, sys, collections

P = r'<本地路径>'
d = open(P, 'rb').read()
ST = 0x1C8
bc = d[ST:]
N = len(bc)
print('bytecode', N, 'file', len(d))


def u16(i):
    return bc[i] | (bc[i + 1] << 8)


def u24(i):
    return bc[i] | (bc[i + 1] << 8) | (bc[i + 2] << 16)


def u32(i):
    return struct.unpack_from('<I', bc, i)[0]


def scan(step_rng, lohi=(0, 19258), label='u16'):
    best = []
    for step in step_rng:
        for off in range(0, min(step, 6)):
            hit = 0
            tot = 0
            p = off
            while p + step + 2 <= N:
                a, b = u16(p), u16(p + step)
                if lohi[0] <= a <= lohi[1] and lohi[0] <= b <= lohi[1]:
                    tot += 1
                    if b == a + 1 or b == a:
                        hit += 1
                p += step
            if tot:
                best.append((hit / tot, hit, tot, step, off))
    best.sort(reverse=True)
    print('==', label, 'top')
    for r in best[:8]:
        print('   ratio %.3f hit %d/%d step %d off %d' % r)


scan(range(2, 18))
scan(range(2, 18), (0, 1003400), 'u16(wide)')

# 任意对齐（不固定步长）的「相邻 +1」对
c = 0
pos = []
for i in range(N - 2):
    if u16(i + 2) == u16(i) + 1 and u16(i) <= 19258:
        c += 1
        pos.append(i)
print('adjacent +1 pairs (stride2, unaligned):', c, pos[:12])
