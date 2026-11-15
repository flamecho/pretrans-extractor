# -*- coding: utf-8 -*-
"""LoverPretend (NS-JP) STCM2L 文本提取 —— 第一版（正文串有序导出）

链路: XCI → NCA → CONTENTS/STORY.cpk（CRI CPK）→ SCRIPT/*.DAT（STCM2L / UTF-8）

字符串节点框架（本作实证，t = 尾标记位置）:
    +0x00 [0]
    +0x04 [L/4]
    +0x08 [1]
    +0x0c [L]              L = align4(byte_len+1)
    +0x10 [utf8 text]      L-1 字节 + NUL
    -0x10 [KIND]           0x104=正文 / 0x13f=名札 / 其它待分类
    -0x0c [0x13a]  -0x08 [id]  -0x04 [0x10]
"""
import os, struct, sys, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SD = os.path.join(VNTRANS_HOME, '_w_lpv/story/SCRIPT')
OUT = os.path.join(VNTRANS_HOME, '_w_lpv/lpv_raw.txt')

U = lambda d, o: struct.unpack_from('<I', d, o)[0]


def scan(d):
    """返回 [(t, L, KIND, text)]，按偏移升序"""
    out = []
    for t in range(0, len(d) - 20):
        if d[t:t + 4] != b'\x00\x00\x00\x00':
            continue
        L = U(d, t + 12)
        if L <= 4 or L > 8192 or L & 3:
            continue
        if U(d, t + 4) != L // 4 or U(d, t + 8) != 1:
            continue
        raw = d[t + 16:t + 16 + L - 1]
        if len(raw) != L - 1:
            continue
        try:
            s = raw.decode('utf-8')
        except UnicodeDecodeError:
            continue
        if any(ord(c) < 0x20 for c in s):
            continue
        out.append((t, L, U(d, t - 16), s))
    return out


if __name__ == '__main__':
    kinds = collections.Counter()
    chars = collections.Counter()
    rows = []
    for f in sorted(os.listdir(SD)):
        if not f.endswith('.DAT'):
            continue
        d = open(os.path.join(SD, f), 'rb').read()
        for t, L, K, s in scan(d):
            kinds[K] += 1
            chars[K] += len(s)
            if K == 0x104:
                rows.append((f, t, s))
    print('KIND 统计（全库）:')
    for k, v in kinds.most_common(12):
        print('   %s n=%6d chars=%8d' % (hex(k), v, chars[k]))
    print('正文节点(0x104) %d 条 / %d 字' % (len(rows), sum(len(x[2]) for x in rows)))
    with open(OUT, 'w', encoding='utf-8') as f:
        for fn, t, s in rows:
            f.write('%s\t%06x\t%s\n' % (fn, t, s))
    print('写出', OUT)
