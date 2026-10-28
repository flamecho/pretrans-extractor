#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""INNOCENT INCEST data.xp3 —— 索引解析（带 flag/adler32），供攻坚探查用。
用法:
  python scripts/incest_xp3.py idx              # 统计 info/segm flag 分布
  python scripts/incest_xp3.py list [--top N]   # 列条目 + flag + adlr
  python scripts/incest_xp3.py get <name>       # 打印某条原始段信息（不解密）
  python scripts/incest_xp3.py adlr <name>      # 原始数据 -> 实际 adler32 vs 索引 adlr
"""
import struct, zlib, sys, os, collections

PATH = '_work_incest/data.xp3'


class Idx:
    def __init__(self, path=PATH):
        self.path = path
        self.sz = os.path.getsize(path)
        with open(path, 'rb') as f:
            head = f.read(0x40)
            off = struct.unpack_from('<Q', head, 0x0b)[0]
            f.seek(off)
            self.raw = f.read()
            if self.raw[:4] != b'File':
                # 索引体：[01][u64 csize][u64 osize][zlib]
                for k in range(0, min(64, len(self.raw) - 2)):
                    if self.raw[k] == 0x78 and self.raw[k + 1] in (0x01, 0x5e, 0x9c, 0xda):
                        self.raw = zlib.decompressobj().decompress(self.raw[k:])
                        break
        self.items = []      # (name, info_flag, [(segflag,off,osize,csize)], adlr)
        p = 0
        while p + 12 <= len(self.raw) and self.raw[p:p+4] == b'File':
            size = struct.unpack_from('<Q', self.raw, p + 4)[0]
            self.items.append(self._file(self.raw[p + 12:p + 12 + size]))
            p += 12 + size

    @staticmethod
    def _file(pl):
        q, name, iflag, segs, adlr = 0, None, 0, [], None
        while q + 12 <= len(pl):
            tag = pl[q:q+4]
            size = struct.unpack_from('<Q', pl, q + 4)[0]
            sp = pl[q + 12:q + 12 + size]
            if tag == b'info':
                iflag = struct.unpack_from('<I', sp, 0)[0]
                nlen = struct.unpack_from('<H', sp, 20)[0]
                name = sp[22:22 + nlen * 2].decode('utf-16-le', 'replace')
            elif tag == b'segm':
                for i in range(0, len(sp) - 27, 28):
                    sf, off, o, c = struct.unpack_from('<IQQQ', sp, i)
                    segs.append((sf, off, o, c))
            elif tag == b'adlr':
                adlr = struct.unpack_from('<I', sp, 0)[0]
            q += 12 + size
        return (name, iflag, segs, adlr)

    def seg_data(self, name):
        it = [x for x in self.items if x[0] == name][0]
        buf = bytearray()
        with open(self.path, 'rb') as f:
            for sf, off, o, c in it[2]:
                f.seek(off)
                raw = f.read(c)
                if sf & 0x80000000 or sf & 7:
                    buf += raw          # 原样（加密/未知）
                else:
                    try:
                        buf += zlib.decompress(raw)
                    except Exception:
                        buf += raw
        return bytes(buf), it


def main():
    a = sys.argv[1:]
    cmd = a[0] if a else 'idx'
    x = Idx()
    if cmd == 'idx':
        print('index bytes = %d, entries = %d' % (len(x.raw), len(x.items)))
        print('info flags:', collections.Counter(hex(i[1]) for i in x.items).most_common(6))
        segf = collections.Counter()
        nseg = collections.Counter()
        for n, f, s, ad in x.items:
            nseg[len(s)] += 1
            for sf, *_ in s:
                segf[hex(sf)] += 1
        print('segs/file:', nseg.most_common(4))
        print('seg flags:', segf.most_common(6))
        # 有 adlr 的条数
        print('has adlr:', sum(1 for i in x.items if i[3] is not None))
        ext = collections.Counter(os.path.splitext(i[0])[1].lower() for i in x.items)
        print('ext:', ext.most_common(8))
    elif cmd == 'list':
        top = 60
        for i, x2 in enumerate(a):
            if x2 == '--top':
                top = int(a[i + 1])
        for n, f, s, ad in x.items[:top]:
            print('%-46s if=%08x segs=%d adlr=%s  %s' % (
                n, f, len(s), '%08x' % ad if ad is not None else '-----',
                ' '.join('%08x:%x/%x' % (sf, o, c) for sf, off, o, c in s[:2])))
    elif cmd == 'get':
        d, it = x.seg_data(a[1])
        print('name=%s iflag=%08x adlr=%08x segs=%r' % (it[0], it[1], it[3], it[2]))
        print('first 64:', d[:64].hex())
    elif cmd == 'adlr':
        d, it = x.seg_data(a[1])
        print('%s  len=%d  real_adler=%08x  idx_adler=%08x  %s' % (
            a[1], len(d), zlib.adler32(d) & 0xffffffff, it[3],
            'OK' if zlib.adler32(d) & 0xffffffff == it[3] else 'MISMATCH'))
    else:
        print(__doc__)


main()
