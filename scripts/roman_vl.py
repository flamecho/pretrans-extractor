# -*- coding: utf-8 -*-
"""召しませ浪漫茶房 (PS2 / SLPM_657.37) —— VSC 'vl_file' 库：vlLZSS 解压 + PAC(MemPack) 读取

链路：ISO9660 → DATA/*.PAC（vlLZSS 整包压缩）→ MemPack 目录（u32 count + count×0x20 条目 + 数据）

vlLZSS（由 SLPM_657.37 `vlCompressDecode` @0x185DF0 反汇编得出；源码路径 D:\\Proj33\\SOURCE\\system\\vl_file\\vlCompress.c）：
  ring 4096B，写指针初值 0xFEE
  flag 字节每 8 项一次，LSB 先行，bit=1 → 字面量
  bit=0 → 双字节 token：off = b0 | ((b1 & 0xF0) << 4)，len = (b1 & 0x0F) + 3
  拷贝源 = ring[(off + k) & 0xFFF]（★ off 是环内绝对位置，不是回退距离）
PAC 头：u32 ver(=1) + u32 decSizeHint(实际以流耗尽为准) + 压缩流
"""
import struct


def lzss(src, limit=None):
    win = bytearray(0x1000)
    w = 0xFEE
    out = bytearray()
    i, n = 0, len(src)
    flag = 0
    while i < n:
        flag >>= 1
        if not (flag & 0x100):
            flag = 0xFF00 | src[i]
            i += 1
        if flag & 1:
            if i >= n:
                break
            c = src[i]
            i += 1
            out.append(c)
            win[w] = c
            w = (w + 1) & 0xFFF
        else:
            if i + 1 >= n:
                break
            b0, b1 = src[i], src[i + 1]
            i += 2
            off = b0 | ((b1 & 0xF0) << 4)
            ln = (b1 & 0x0F) + 3
            for k in range(ln):
                c = win[(off + k) & 0xFFF]
                out.append(c)
                win[w] = c
                w = (w + 1) & 0xFFF
        if limit and len(out) >= limit:
            break
    return bytes(out[:limit]) if limit else bytes(out)


def pac_entries(blob):
    """-> [(name, off, size)]；数据区起点 = 0x10 + count*0x20，逐条按 0x40 对齐累加"""
    cnt, = struct.unpack_from('<I', blob, 0)
    ents = []
    off = 0x10 + cnt * 0x20
    for i in range(cnt):
        o = 0x10 + i * 0x20
        name = blob[o:o + 16].split(b'\0')[0].decode('cp932', 'replace')
        size, = struct.unpack_from('<I', blob, o + 0x10)
        ents.append((name, off, size))
        off += (size + 0x3F) & ~0x3F
    return ents


def open_pac(path):
    d = open(path, 'rb').read()
    blob = lzss(d[8:])
    return blob, pac_entries(blob)


if __name__ == '__main__':
    import sys
    for p in sys.argv[1:]:
        b, e = open_pac(p)
        print('==', p, 'dec', len(b), 'files', len(e))
        for nm, off, sz in e:
            print('   %08x %8d %s' % (off, sz, nm))
