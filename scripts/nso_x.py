#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NSO0 -> 平铺镜像（text/rodata/data 依次拼接，LZ4 段自动解压）。

用法: python nso_x.py <main|subsdk...> <out.bin>

NSO0 头（switchbrew）:
  0x00 "NSO0" | 0x04 ver | 0x08 reserved | 0x0C flags
  0x10 text.file / 0x14 text.mem / 0x18 text.size
  0x20 ro.file   / 0x24 ro.mem   / 0x28 ro.size
  0x30 data.file / 0x34 data.mem / 0x38 data.size
  0x60 text.comp / 0x64 ro.comp  / 0x68 data.comp
  flags bit0/1/2 = text/ro/data 压缩（LZ4 block）
"""
import sys


def lz4_block(src, usize):
    dst = bytearray()
    i, n = 0, len(src)
    while i < n:
        tok = src[i]
        i += 1
        lit = tok >> 4
        if lit == 15:
            while i < n:
                b = src[i]
                i += 1
                lit += b
                if b != 255:
                    break
        dst += src[i:i + lit]
        i += lit
        if i + 2 > n or len(dst) >= usize:
            break
        off = src[i] | (src[i + 1] << 8)
        i += 2
        if off == 0:
            break
        mlen = tok & 0xF
        if mlen == 15:
            while i < n:
                b = src[i]
                i += 1
                mlen += b
                if b != 255:
                    break
        mlen += 4
        start = len(dst) - off
        if start < 0:
            raise ValueError('bad lz4 stream at %#x' % i)
        for k in range(mlen):
            dst.append(dst[start + k])
        if len(dst) > usize:
            del dst[usize:]
            break
    return bytes(dst[:usize])


def u32(d, o):
    return int.from_bytes(d[o:o + 4], 'little')


def main():
    d = open(sys.argv[1], 'rb').read()
    assert d[:4] == b'NSO0', d[:4]
    flags = u32(d, 0x0C)
    segs = []
    for k, (fo, ms, sz, cs) in enumerate(((u32(d, 0x10), u32(d, 0x14), u32(d, 0x18), u32(d, 0x60)),
                                          (u32(d, 0x20), u32(d, 0x24), u32(d, 0x28), u32(d, 0x64)),
                                          (u32(d, 0x30), u32(d, 0x34), u32(d, 0x38), u32(d, 0x68)))):
        if sz == 0:
            continue
        comp = (flags >> k) & 1
        raw = d[fo:fo + (cs if comp else sz)]
        seg = lz4_block(raw, sz) if comp else raw
        print('seg%d file=%#x comp=%d size=%d -> %d' % (k, fo, len(raw), sz, len(seg)))
        segs.append((ms, seg))
    out = bytearray()
    base = min(ms for ms, _ in segs) if segs else 0
    for ms, seg in segs:
        pad = (ms - base) - len(out)
        if pad > 0:
            out += b'\x00' * pad
        out += seg
    open(sys.argv[2], 'wb').write(bytes(out))
    print('total %d  (base mem %#x)' % (len(out), base))


if __name__ == '__main__':
    main()
