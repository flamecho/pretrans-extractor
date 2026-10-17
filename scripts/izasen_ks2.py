#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""いざ、出陣！恋戦 data.cpk → scenario/*.ks（终版）

结论（2026-10-18 实证，工具 kuriimu2 CrilaylaDecoder.cs 为参考实现）：
  * CPK 表 FileOffset 列相对行错位一行 ⇒ 文件 i 的块起点 = rows[i+1].FileOffset（1122/1122 尺寸校验通过）
  * CRILAYLA 头：u32@8　　= 明文长度（不含 0x100 原样前缀）⇒ 输出 = usize + 0x100
                u32@12 = 压缩流长度；原样前缀位于 16+csize 起 0x100 字节
  * ★count 为**变长编码**（2/3/5/8 位阶梯），按固定 8 位读会中途耗尽码流（本项目最初 42% 失败的原因）
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from izasen_cpk import CPK932


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


def safe(name):
    name = name.replace('\\', '/').lstrip('/')
    name = ''.join(('_' if ch in '<>:"|?*' or ord(ch) < 32 else ch) for ch in name)
    return name.replace('/', '_')


def main():
    cpk, outdir = sys.argv[1], sys.argv[2]
    ext = sys.argv[3] if len(sys.argv) > 3 else '.ks'
    c = CPK932(cpk)
    data = open(cpk, 'rb').read()
    t, _ = c._read_utf_at(c.TocOffset)
    rows = t.rows
    os.makedirs(outdir, exist_ok=True)
    n = 0
    bad = []
    for i in range(len(rows) - 1):
        r = rows[i]
        name = r.get('FileName') or ''
        if ext and not name.lower().endswith(ext):
            continue
        o = rows[i + 1].get('FileOffset') or 0
        if o <= 0 or o >= len(data):
            bad.append((name, 'off'))
            continue
        if data[o:o + 8] == b'CRILAYLA':
            cs = struct.unpack_from('<I', data, o + 12)[0]
            try:
                buf = crilayla(data[o:o + 16 + cs + 0x100])
            except Exception as e:
                bad.append((name, 'crilayla:%s' % e))
                continue
        else:
            fs = r.get('FileSize') or 0
            buf = data[o:o + fs].rstrip(b'\x00')
        with open(os.path.join(outdir, safe(name)), 'wb') as fh:
            fh.write(buf)
        n += 1
    print('extracted', n, 'bad', len(bad))
    for b in bad[:10]:
        print('  BAD', b)


if __name__ == '__main__':
    main()
