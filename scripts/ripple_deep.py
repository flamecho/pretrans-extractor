#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""递归解 HFU2（含嵌套），输出叶子 blob 并统计日文密度。"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arcanafesta_extract import lzs_decode


def split(data):
    """返回 [(off,size,size2,blob)]；非 HFU2 返回 None"""
    if data[:4] != b'HFU2':
        return None
    cnt = struct.unpack_from('<I', data, 4)[0]
    X = struct.unpack_from('<I', data, 8)[0]
    tab = 0x10
    if cnt > 4000 or tab + cnt * 16 > len(data):
        return None
    out = []
    for k in range(cnt):
        o, s, s2, h = struct.unpack_from('<IIII', data, tab + k * 16)
        p = X + o
        blob = b''
        if p + 16 <= len(data) and data[p:p + 4] == b'UFFA':
            cs, us = struct.unpack_from('<II', data, p + 4)
            blob = lzs_decode(data[p + 16:p + 16 + cs], us)
        elif p < len(data):
            blob = data[p:p + s]
        out.append((o, s, s2, blob))
    return out


def leaves(data, depth=0, path=''):
    """深度展开，直至 blob 不是 HFU2"""
    subs = split(data) if depth < 4 else None
    if subs is None:
        yield path, data
        return
    for k, (o, s, s2, blob) in enumerate(subs):
        yield from leaves(blob, depth + 1, '%s/%d' % (path, k))


def jp_score(b):
    """近似日文密度：cp932 双字节假名/汉字计分"""
    kana = 0
    for i in range(len(b) - 1):
        c = b[i] << 8 | b[i + 1]
        if 0x829f <= c <= 0x82f1 or 0x8340 <= c <= 0x8396:
            kana += 1
    return kana


if __name__ == '__main__':
    src, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    ls = list(leaves(open(src, 'rb').read()))
    print('%s -> %d leaves' % (src, len(ls)))
    idx = 0
    for path, b in ls:
        if len(b) < 32:
            continue
        sc = jp_score(b)
        fn = os.path.join(outdir, ('%03d' % idx) + path.replace('/', '_') + '.bin')
        if len(b) < 4 * 1024 * 1024:
            open(fn, 'wb').write(b)
        print('  %-14s len=%8d kana=%6d %s' % (path, len(b), sc, os.path.basename(fn)))
        idx += 1
