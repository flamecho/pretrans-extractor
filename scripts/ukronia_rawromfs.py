#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「LZ4 桶树压缩 NCA」的 RomFS 段还原成裸 romfs 镜像（供 bktr_romfs.py --base 使用）。

背景：泡沫のユークロニア 的 base NCA 是压缩 NCA（section1 = 桶树 LZ4），
而 scripts/bktr_romfs.py 的 PlainReader 只能吃裸 romfs / 未压缩 NCA / XCI，
所以先本工具落一份 raw image，再交给 bktr_romfs 做 BKTR 虚拟读。

复用 scripts/ukronia_nca.py 的 Sec / BucketRomfs（只读 import，不改原文件）。

用法：python scripts/ukronia_rawromfs.py <base.nca> <out.romfs> [--sec 1]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import ukronia_nca as U


def main():
    nca, out = sys.argv[1], sys.argv[2]
    sid = 1
    for i, a in enumerate(sys.argv):
        if a == '--sec':
            sid = int(sys.argv[i + 1])
    sec = U.Sec(nca)
    b = U.BucketRomfs(sec, sid)
    b.sid = sid
    total = b.total
    print('[i] buckets=%d entries=%d total=%d (%.2f GB)' % (b.nbucket, len(b.ents), total, total / 2**30))
    written = 0
    with open(out, 'wb') as w:
        w.truncate(total)
        for i in range(len(b.ents)):
            blk = b.block(i)
            v = b.ents[i][0]
            n = min(len(blk), total - v)
            if n <= 0:
                continue
            w.seek(v)
            w.write(blk[:n])
            written += n
            if i % 200 == 0:
                print('   %d/%d  v=%#x  +%d' % (i, len(b.ents), v, n), flush=True)
    print('[i] wrote %d B -> %s (size %d)' % (written, out, os.path.getsize(out)))


if __name__ == '__main__':
    main()
