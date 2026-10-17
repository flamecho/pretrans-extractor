#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""いざ、出陣！恋戦 data.cpk → 剧本流还原

★本作 CPK 的数据区不是「一文件一块」，而是**全部文件串接成一条逻辑字节流**，
  再按 2048 B 切成块；每块或原样存储、或独立 CRILAYLA 压缩（块首 magic 自述）。
  TOC 的 FileOffset/FileSize 因此只对「块」有意义（比文件粒度粗）⇒ 必须按流还原后
  以每文件首行注释 `; <name>.ks` 切分。这是最初按「条目=文件」解包只有 42% 成功的原因。

CRILAYLA（kuriimu2 CrilaylaDecoder.cs 为准）：
  magic[8] + u32 明文长度(不含 0x100 前缀) + u32 压缩流长度 + 压缩流 + 0x100 原样前缀
  count 为变长编码（2/3/5/8 阶梯 + 3）
"""
import os
import struct
import sys

CONTENT_OFFSET = 280576   # CPK 头 ContentOffset


def crilayla(blk):
    usize, csize = struct.unpack_from('<II', blk, 8)
    src = blk[16:16 + csize]
    pre = blk[16 + csize:16 + csize + 0x100]
    out = bytearray(pre) + bytearray(usize)
    sp = len(src) - 1
    bc = 0
    bd = 0
    dp = len(out) - 1

    def gb(k):
        nonlocal sp, bc, bd
        while bc < k:
            bd = ((bd << 8) | src[sp]) & 0xFFFFFFFF
            sp -= 1
            bc += 8
        r = (bd >> (bc - k)) & ((1 << k) - 1)
        bc -= k
        return r

    def rlen():
        l = gb(2)
        if l != 3:
            return l
        m = gb(3)
        l += m
        if m != 7:
            return l
        m = gb(5)
        l += m
        if m != 31:
            return l
        while True:
            m = gb(8)
            l += m
            if m != 0xFF:
                return l

    while dp >= 0x100:
        if gb(1):
            disp = gb(13) + 3
            cnt = rlen() + 3
            for _ in range(cnt):
                if dp < 0x100:
                    break
                out[dp] = out[dp + disp]
                dp -= 1
        else:
            out[dp] = gb(8)
            dp -= 1
    return bytes(out)


def main():
    cpk = sys.argv[1]
    out = sys.argv[2]
    data = open(cpk, 'rb').read()
    stream = bytearray()
    o = CONTENT_OFFSET
    blocks = 0
    comp = 0
    while o + 16 < len(data):
        if data[o:o + 8] == b'CRILAYLA':
            us, cs = struct.unpack_from('<II', data, o + 8)
            stream += crilayla(data[o:o + 16 + cs + 0x100])
            comp += 1
            span = ((16 + cs + 0x100) + 2047) // 2048 * 2048
            o += max(2048, span)
        else:
            stream += data[o:o + 2048]
            o += 2048
        blocks += 1
    # 去掉末尾对齐填充
    while stream and stream[-1] == 0:
        stream.pop()
    with open(out, 'wb') as fh:
        fh.write(stream)
    print('blocks', blocks, 'crilayla', comp, 'stream bytes', len(stream))


if __name__ == '__main__':
    main()
