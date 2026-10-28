#!/usr/bin/env python3
"""Konami tkl 'type 2' (flags&0xF==2) 解压器 —— 逆向自 SLPM_662.47 0x135e30。

算法（已用 unicorn 直跑原机代码逐字节比对通过）:
  载荷 = [u32le 剩余字节数] + 若干 block，block 依次铺满整个载荷
  block:
    词表复位: tab0[i]=i, tab1[i]=0, pos=0
    prelude（描述本块用到的"字典节点"）:
       c = 读 1 字节
       c >= 0x80 : pos += c-0x7f; 若 pos >= 256 → prelude 结束; n = 0
       c <  0x80 : n = c
       do n+1 次:
           v = 读 1 字节; tab0[pos] = v
           若 v != pos: tab1[pos] = 读 1 字节      # 复合节点 = (v, tab1[pos])
           pos += 1
    u16le N  = 根码个数; 随后 N 个字节为根码
    展开: pop s; 若 tab0[s]==s → 输出 s; 否则 push tab1[s] 再 push tab0[s]
      （即先展开 tab0[s] 子树、后展开 tab1[s] 子树）
  剩余字节数 == 0 时结束。

用法: python scripts/ml2_type2.py <in.bin> [out.bin] [usize]
"""
import sys


def decode(src, usize=None, strict=True):
    if len(src) < 4:
        raise ValueError('type2 payload too short')
    t0 = int.from_bytes(src[0:4], 'little')
    p = 4
    out = bytearray()
    blocks = 0
    while True:
        blocks += 1
        tab0 = list(range(256))
        tab1 = [0] * 256
        pos = 0
        while True:
            c = src[p]; p += 1; t0 -= 1
            if c >= 0x80:
                pos += c - 0x7f
                if pos >= 0x100:
                    break
                n = 0
            else:
                n = c
            for _ in range(n + 1):
                v = src[p]; p += 1; t0 -= 1
                tab0[pos] = v
                if v != pos:
                    tab1[pos] = src[p]; p += 1; t0 -= 1
                pos += 1
            if pos >= 0x100:          # 0x135f78: 词表槽位写满即结束 prelude
                break
        N = src[p] | (src[p + 1] << 8)
        p += 2; t0 -= 2
        stack = []
        while True:
            if not stack:
                if N == 0:
                    break
                N -= 1
                stack.append(src[p]); p += 1; t0 -= 1
            s = stack.pop()
            if tab0[s] == s:
                out.append(s)
            else:
                stack.append(tab1[s])
                stack.append(tab0[s])
        if t0 <= 0:
            break
    if strict:
        if t0 != 0:
            raise ValueError('type2: leftover t0=%d (misparse)' % t0)
        if p != len(src):
            raise ValueError('type2: consumed %d of %d' % (p, len(src)))
        if usize is not None and len(out) != usize:
            raise ValueError('type2: usize mismatch %d != %d' % (len(out), usize))
    return bytes(out)


if __name__ == '__main__':
    data = open(sys.argv[1], 'rb').read()
    us = int(sys.argv[3], 0) if len(sys.argv) > 3 else None
    out = decode(data, us)
    print('ok %d bytes' % len(out))
    if len(sys.argv) > 2:
        open(sys.argv[2], 'wb').write(out)
