#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""5pb PSP MARC font-atlas renderer (ar999_0000.bin).
The atlas is 8bpp ALPHA (the 64-byte header is an alpha ramp palette, NOT an index table):
render the raw bytes as grayscale, do NOT multiply by 17.
unswizzle: 32x8 blocks, W=512  ->  blk=(y//8)*(W//32)+(x//32), off=blk*256+(y%8)*32+(x%32)
Usage: python render_atlas.py ar999_0000.bin [out.png]
"""
import sys, struct
from PIL import Image

W, H = 512, 872


def main():
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else 'atlas_a.png'
    d = open(src, 'rb').read()
    assert d[:4] == b'MARC'
    off, end = struct.unpack_from('<II', d, 8)          # e0 = atlas
    e0 = d[off:end]
    px = e0[64:]                                        # skip 64B palette
    buf = bytearray(W * H)
    for y in range(H):
        for x in range(W):
            blk = (y // 8) * (W // 32) + (x // 32)
            o = blk * 256 + (y % 8) * 32 + (x % 32)
            buf[y * W + x] = px[o] if o < len(px) else 0
    Image.frombytes('L', (W, H), bytes(buf)).save(out)
    print('wrote', out, '(8bpp alpha; cells are 8x8, 64 cols x %d rows)' % (H // 8))


if __name__ == '__main__':
    main()
