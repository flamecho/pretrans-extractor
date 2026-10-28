# -*- coding: utf-8 -*-
"""硝子の森 (PS2-JP / D3PUBLISHER SIMPLE2000 Vol.13 / HuneX "ebf") 容器 + LZSS

链路：
  ISO9660 → EVENTDAT.BIN（PACK）→ member → 子 PACK（头 0x950）→ LZSS 块 → ebf 模块

PACK:
  +0x00 'PACK' | +0x04 u32 count | +0x08 u32 0x800 | +0x0c u32 flag | +0x10 u32 0
  +0x14 ... 条目表起点实为 +0x18：[u32 offset][u32 size]，0x800 对齐，0xFFFFFFFF 终止

LZSS 块（16 字节头）：
  +0x00 'LZSS' | +0x04 u32 blockSize（含头，下一块 = 本块 + blockSize）
  +0x08 u32 decompSize | +0x0c u32 0 | +0x10 payload

LZSS 解码（已由 SLPM_622.34 的压缩器 0x141218 交叉验证）：
  flag 字节，1 位/令牌，LSB 优先，bit=1 ⇒ 1 字节字面量
  bit=0 ⇒ 2 字节匹配 [a][b]：offset = a | ((b>>4)<<8)，length = (b & 0xF) + 3 （3..18）
  窗口 0x1000，初始全 0
用法：
  python scripts/glasu_extract.py <EVENTDAT.BIN> <outdir>   # 导出每个 LZSS 块解压后的 ebf
"""
import os
import struct
import sys


def lzss(src, outsize=1 << 24, N=0x1000):
    """★窗口起始位置 0xFEE（不是 0）。写窗口与读窗口用同一个 4096 环。"""
    win = bytearray(N)
    r = 0xFEE
    out = bytearray()
    p = 0
    n = len(src)
    flags = 0
    while p < n and len(out) < outsize:
        flags >>= 1
        if (flags & 0x100) == 0:
            flags = src[p] | 0xFF00
            p += 1
        if flags & 1:
            c = src[p]; p += 1
            out.append(c); win[r] = c; r = (r + 1) % N
        else:
            a, b = src[p], src[p + 1]; p += 2
            o = a | ((b >> 4) << 8)
            ln = (b & 0xF) + 3
            for _ in range(ln):
                c = win[o % N]; o += 1
                out.append(c); win[r] = c; r = (r + 1) % N
    return bytes(out)


def pack_entries(d):
    n = struct.unpack_from('<I', d, 4)[0]
    out = []
    for i in range(n):
        o, s = struct.unpack_from('<II', d, 0x18 + i * 8)
        if o == 0xffffffff:
            break
        out.append((o, s))
    return out


def blocks(d, start, end, limit=100000):
    off = start
    res = []
    while off + 16 <= end and len(res) < limit:
        if d[off:off + 4] != b'LZSS':
            off += 4
            continue
        comp, dec, unk = struct.unpack_from('<III', d, off + 4)
        if comp < 16 or comp > 1 << 22 or dec > 1 << 24:
            off += 4
            continue
        res.append((off, comp, dec))
        off += comp
    return res


def main():
    path, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    d = open(path, 'rb').read()
    total = 0
    for mi, (o, s) in enumerate(pack_entries(d)):
        for bi, (boff, comp, dec) in enumerate(blocks(d, o, o + s)):
            raw = lzss(d[boff + 16:boff + comp], dec)
            open(os.path.join(outdir, 'm%02d_b%03d.bin' % (mi, bi)), 'wb').write(raw)
            total += 1
    print('blocks', total)


if __name__ == '__main__':
    main()
