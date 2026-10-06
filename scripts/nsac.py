#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NSAC (v2) 容器解析/解包 —— eXtend 系 PSVita 作品《逢魔が刻 ～かくりよの縁～》(PCSG00769)

格式 (逆向结论)
---------------
  0x00  char[4]  "NSAC"
  0x04  u16      version (=2)
  0x06  u16      count               条目数
  0x08  u32      totalSize           整档字节数
  0x0c  u32      dataBase            数据区起点 (通常 0x600)
  0x10  u32      count*10            条目表字节数
  0x14  u32      ?                    (疑似 hash / 校验)
  0x18  u32      ? (=2)
  ...
  0x26  count × { u16 idx, u32 offset, u32 size }   条目表 (按 idx 排序)
  0x26+count*10  count × { name NUL-terminated } + { u16 ?, u32 offset, u32 size }
                名字表 (逐条: 名字以 0x00 结束, 紧随 10 字节 = 同上三元组)
  dataBase      数据区 (各条目 offset/size 指向此处)

用法:
    python nsac.py <file.dat> [outdir]     # 给出 outdir 则解包
"""
import os
import struct
import sys


class Nsac:
    def __init__(self, b):
        self.b = b
        self.magic = b[:4]
        self.ver, self.count = struct.unpack_from('<HH', b, 4)
        self.total = struct.unpack_from('<I', b, 8)[0]
        self.database = struct.unpack_from('<I', b, 0xc)[0]
        self.tabsize = struct.unpack_from('<I', b, 0x10)[0]
        self.entries = []       # (idx, off, size)
        self.named = []         # (name, off, size)
        self._parse()

    def _parse(self):
        b = self.b
        if b[:4] != b'NSAC':
            return
        off = 0x26
        for i in range(self.count):
            idx, o, s = struct.unpack_from('<HII', b, off)
            self.entries.append((idx, o, s))
            off += 10
        # 名字表
        p = off
        for i in range(self.count):
            e = b.find(b'\x00', p)
            if e < 0:
                break
            name = b[p:e].decode('cp932', 'replace')
            a, o, s = struct.unpack_from('<HII', b, e + 1)
            self.named.append((name, o, s))
            p = e + 1 + 10
        self.nametab_end = p

    def read(self, name):
        for n, o, s in self.named:
            if n == name:
                return self.b[o:o + s]
        return None

    def extract(self, outdir):
        os.makedirs(outdir, exist_ok=True)
        n = 0
        for name, o, s in self.named:
            safe = name.replace('/', '_').replace('\\', '_')
            with open(os.path.join(outdir, safe), 'wb') as f:
                f.write(self.b[o:o + s])
            n += 1
        return n


def main():
    if len(sys.argv) < 2:
        sys.stderr.write(__doc__)
        sys.exit(2)
    path = sys.argv[1]
    b = open(path, 'rb').read()
    a = Nsac(b)
    print('magic=%s ver=%d count=%d total=%d database=0x%x tabsize=%d nametab_end=0x%x' %
          (a.magic, a.ver, a.count, a.total, a.database, a.tabsize, a.nametab_end))
    for name, o, s in a.named:
        print('  %-40s off=0x%08x size=%d' % (name, o, s))
    if len(sys.argv) >= 3:
        n = a.extract(sys.argv[2])
        print('extracted %d files -> %s' % (n, sys.argv[2]))


if __name__ == '__main__':
    main()
