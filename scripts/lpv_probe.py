# -*- coding: utf-8 -*-
"""LoverPretend / STCM2L 节点探针：找 [0][L/4][1][L][utf8 text] 强签名。"""
import sys, struct, collections

KANA = set(chr(c) for c in range(0x3041, 0x30FF))


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def scan(d):
    out = []
    for i in range(12, len(d) - 16):
        if d[i] != 1 or d[i + 1] or d[i + 2] or d[i + 3]:
            continue
        L = u32(d, i + 4)
        if L < 8 or L > 8192 or L & 3:
            continue
        if u32(d, i - 4) != L // 4 or u32(d, i - 8) != 0:
            continue
        raw = d[i + 8:i + 8 + L - 1]
        try:
            s = raw.decode('utf-8')
        except UnicodeDecodeError:
            continue
        if not s or any(ord(c) < 0x20 for c in s):
            continue
        if sum(1 for c in s if c in KANA) / len(s) < 0.15:
            continue
        out.append((i, L, s))
    return out


if __name__ == '__main__':
    for p in sys.argv[1:]:
        d = open(p, 'rb').read()
        hits = scan(d)
        print('==', p, 'size', len(d), 'hits', len(hits))
        for i, L, s in hits[:8]:
            print('   %6x L=%4d %r' % (i, L, s[:60]))
