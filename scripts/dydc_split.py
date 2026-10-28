#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""XCI → secure 分区 NCA 手切（nsz 还原的 XCI 哈希不被 hactool 接受，故手工走 HFS0 链）。

结构（本族实证，无对齐填充）：
  root HFS0 @0xF000：count=4 / strtab={"update","logo","normal","secure"}
  子分区紧接 root 数据区依次排列，每个 HFS0：0x10 头 + count*0x40 条目 + strtab，条目 offset 相对数据区
  条目 = { u64 offset; u64 size; u32 name_off; u32 hashed_size }

用法: python scripts/dydc_split.py <xci> <outdir>
"""
import os
import struct
import sys


def parse_hfs0(f, base):
    f.seek(base)
    magic, cnt, strsz, _z = struct.unpack('<4sIII', f.read(0x10))
    if magic != b'HFS0':
        raise ValueError('no HFS0 @ %#x: %r' % (base, magic))
    strtab = base + 0x10 + cnt * 0x40
    data_b = strtab + strsz
    ents = []
    for i in range(cnt):
        f.seek(base + 0x10 + i * 0x40)
        off, size, name_off, hsz = struct.unpack('<QQII', f.read(0x18))
        f.seek(strtab + name_off)
        nm = b''
        while True:
            c = f.read(1)
            if c in (b'\x00', b''):
                break
            nm += c
        ents.append({'name': nm.decode('utf-8', 'replace'),
                     'off': data_b + off, 'size': size, 'hsz': hsz})
    total = max([e['off'] + e['size'] for e in ents], default=data_b) - data_b
    return ents, data_b, total


def main():
    xci, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    with open(xci, 'rb') as f:
        root, rbase, _ = parse_hfs0(f, 0xF000)
        print('root:', [e['name'] for e in root])
        sec = None
        for e in root:
            count, base, total = parse_hfs0(f, e['off'])
            print('  partition %-7s @ %#010x cnt=%d' % (e['name'], e['off'], len(count)))
            if e['name'] == 'secure':
                sec = count
        for e in sec:
            f.seek(e['off'])
            p = os.path.join(outdir, e['name'])
            with open(p, 'wb') as w:
                left = e['size']
                while left > 0:
                    b = f.read(min(1 << 24, left))
                    if not b:
                        break
                    w.write(b)
                    left -= len(b)
            print('    %-44s %14d' % (e['name'], e['size']))


if __name__ == '__main__':
    main()
