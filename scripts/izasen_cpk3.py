#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""いざ、出陣！恋戦 data.cpk → .ks 解包（v3）

两处关键修正（2026-10-18 实证）：
  1. TOC 的 FileOffset 列相对行**错位一行**：文件 i 的块起点 = rows[i+1].FileOffset
     （校验：每行 FileSize == 16+csize+0x100、ExtractSize == usize+0x100，1128/1134 命中）
  2. CRILAYLA 头 u32@8 = **不含 0x100 前缀**的明文长度 ⇒ 总长 = usize + 0x100
     （标准实现按 usize 当总长会越界；原 scripts/cpk_v1.py 另有 "offset 再加 ContentOffset" 的错误）
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from izasen_cpk import CPK932


def crilayla(block):
    usize, csize = struct.unpack_from('<II', block, 8)
    src = block[16:16 + csize]
    pre = block[16 + csize:16 + csize + 0x100]
    out = bytearray(pre) + bytearray(usize)
    sp = len(src) - 1
    dp = len(out) - 1
    bitcnt = 0
    bitdat = 0

    def get_bits(n):
        nonlocal sp, bitcnt, bitdat
        while bitcnt < n:
            bitdat = ((bitdat << 8) | src[sp]) & 0xFFFFFFFF
            sp -= 1
            bitcnt += 8
        r = (bitdat >> (bitcnt - n)) & ((1 << n) - 1)
        bitcnt -= n
        return r

    while dp >= 0x100:
        if get_bits(1):
            off = get_bits(13) + 3
            cnt = get_bits(8) + 3
            for _ in range(cnt):
                if dp < 0x100:
                    break
                out[dp] = out[dp + off]
                dp -= 1
        else:
            out[dp] = get_bits(8)
            dp -= 1
    return bytes(out)


def safe(rel):
    rel = rel.replace('\\', '/').lstrip('/')
    rel = ''.join(('_' if ch in '<>:"|?*' or ord(ch) < 32 else ch) for ch in rel)
    return '/'.join(p.rstrip(' .') or '_' for p in rel.split('/'))


def main():
    cpk, outdir = sys.argv[1], sys.argv[2]
    only = sys.argv[3] if len(sys.argv) > 3 else '.ks'
    c = CPK932(cpk)
    data = open(cpk, 'rb').read()
    t, _ = c._read_utf_at(c.TocOffset)
    rows = t.rows
    n = 0
    bad = []
    for i in range(len(rows) - 1):
        r = rows[i]
        name = (r.get('DirName') or '') + '/' + (r.get('FileName') or '')
        if only and not name.lower().endswith(only):
            continue
        o = rows[i + 1].get('FileOffset') or 0
        fs = r.get('FileSize') or 0
        if o <= 0 or o >= len(data):
            bad.append((name, 'off'))
            continue
        if data[o:o + 8] == b'CRILAYLA':
            usize, csize = struct.unpack_from('<II', data, o + 8)
            try:
                buf = crilayla(data[o:o + 16 + csize + 0x100])
            except Exception as e:
                bad.append((name, 'crilayla:%s' % e))
                continue
        else:
            buf = data[o:o + fs].rstrip(b'\x00')
        dst = os.path.join(outdir, *safe(name).split('/'))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, 'wb') as fh:
            fh.write(buf)
        n += 1
    print('extracted', n, 'bad', len(bad))
    for b in bad[:12]:
        print('  BAD', b)


if __name__ == '__main__':
    main()
