#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""水の旋律 ～協奏曲～ (PC, KID/mlk ADV 引擎) ARC0 归档解包
格式: "ARC0" + u32 count + 0x10000 保留块 + index(0x10008, count*268)
记录 268B: char name[256] + u32 size + u32 offset + u32 flag
条目: 前 0x100 字节 XOR (位序 i), 其后为 zlib 流
用法: python scripts/mizumelody_arc.py <ARCHIVE.BIN> <outdir> [--list]
"""
import os, struct, sys, zlib

REC = 268
IDX = 0x10008


def load(path):
    d = open(path, 'rb').read()
    assert d[:4] == b'ARC0', d[:4]
    count = struct.unpack_from('<I', d, 4)[0]
    recs = []
    for i in range(count):
        o = IDX + i * REC
        r = bytearray(d[o:o + REC])
        for j in range(min(0x100, REC)):
            r[j] ^= j
        nm = bytes(r[:256]).split(b'\x00')[0].decode('cp932', 'replace')
        size, off, flag = struct.unpack_from('<III', r, 256)
        recs.append((nm, size, off, flag))
    return d, recs


def entry(d, off, size):
    buf = bytearray(d[off:off + size])
    for i in range(min(0x100, len(buf))):
        buf[i] ^= i
    return zlib.decompress(bytes(buf))


def main():
    src, outdir = sys.argv[1], sys.argv[2]
    d, recs = load(src)
    os.makedirs(outdir, exist_ok=True)
    bad = 0
    for nm, size, off, flag in recs:
        if not nm or size == 0 or off >= len(d):
            continue
        try:
            data = entry(d, off, size)
        except Exception as e:
            print('FAIL', nm, e); bad += 1; continue
        p = os.path.join(outdir, nm.replace('/', os.sep))
        os.makedirs(os.path.dirname(p), exist_ok=True) if os.path.dirname(p) else None
        open(p, 'wb').write(data)
    print('entries', len(recs), 'fail', bad)


if __name__ == '__main__':
    main()
