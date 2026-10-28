#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""リプルのたまご (PS2) HFU2 解包 + 目视 dump 用。"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arcanafesta_extract import lzs_decode


def hfu2_entries(data):
    assert data[:4] == b'HFU2', data[:4]
    cnt = struct.unpack_from('<I', data, 4)[0]
    X = struct.unpack_from('<I', data, 8)[0]
    tab = 0x10
    out = []
    for k in range(cnt):
        o, s, s2, h = struct.unpack_from('<IIII', data, tab + k * 16)
        p = X + o
        blob = b''
        if data[p:p + 4] == b'UFFA':
            cs, us = struct.unpack_from('<II', data, p + 4)
            blob = lzs_decode(data[p + 16:p + 16 + cs], us)
        out.append((o, s, s2, blob))
    return out


def main():
    src = sys.argv[1]
    outdir = sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    data = open(src, 'rb').read()
    ents = hfu2_entries(data)
    print('%s: %d entries' % (src, len(ents)))
    for k, (o, s, s2, blob) in enumerate(ents):
        p = os.path.join(outdir, 'e%03d.bin' % k)
        open(p, 'wb').write(blob)
        print('  e%03d off=%#x size=%#x out=%#x dec=%#x' % (k, o, s, s2, len(blob)))


if __name__ == '__main__':
    main()
