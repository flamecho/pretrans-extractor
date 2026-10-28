#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""even if TEMPEST 本体（未压缩 romfs NCA）→ 裸 romfs 镜像（0 = romfs 头）。

只读复用 scripts/nsp_plainromfs.py 的 open_nsp / SecView，不改原脚本。

用法: python scripts/dump_base.py <base.nsp> <out.romfs>
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import nsp_plainromfs as W4


def main():
    src, out = sys.argv[1], sys.argv[2]
    n, v, comp = W4.open_nsp(src)
    if comp[0] or comp[1]:
        raise SystemExit('压缩段，改用 ukronia_rawromfs.py')
    lv5 = n.fsh[0x18 + 5 * 0x18:0x18 + 5 * 0x18 + 0x10]
    import struct
    off, size = struct.unpack('<QQ', lv5)
    print('[i] level5 @%#x size=%d (%.2f GB)' % (off, size, size / 2**30))
    with open(out, 'wb') as w:
        w.truncate(size)
        step = 1 << 24
        for k in range(0, size, step):
            w.seek(k)
            w.write(v.read(k, min(step, size - k)))
            if (k // step) % 32 == 0:
                print('   %d/%d' % (k, size), flush=True)
    print('[i] wrote %d B -> %s' % (os.path.getsize(out), out))


if __name__ == '__main__':
    main()
