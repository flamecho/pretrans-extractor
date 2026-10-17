#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""いざ、出陣！恋戦 data.cpk 解包（v2：CRILAYLA 修正 + FileOffset 绝对偏移）"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from izasen_cpk import CPK932


def crilayla(block):
    """本作变体：u32@8 = 压缩后明文长度(不含 0x100 前缀)，总长 = usize + 0x100。"""
    usize, csize = struct.unpack_from('<II', block, 8)
    src = block[16:16 + csize]
    pre = block[16 + csize:16 + csize + 0x100]
    out = bytearray(pre) + bytearray(usize)
    sp = len(src) - 1
    dp = usize - 1
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


def main():
    cpk = sys.argv[1]
    outdir = sys.argv[2]
    only = sys.argv[3] if len(sys.argv) > 3 else '.ks'
    c = CPK932(cpk)
    data = open(cpk, 'rb').read()
    t, _ = c._read_utf_at(c.TocOffset)
    n = 0
    bad = []
    for r in t.rows:
        name = (r.get('DirName') or '') + '/' + (r.get('FileName') or '')
        if only and not name.lower().endswith(only):
            continue
        off = r.get('FileOffset') or 0
        if off <= 0 or off >= len(data):
            bad.append((name, 'off'))
            continue
        if data[off:off + 8] == b'CRILAYLA':
            usize, csize = struct.unpack_from('<II', data, off + 8)
            try:
                buf = crilayla(data[off:off + 16 + csize + 0x100])
            except Exception as e:
                bad.append((name, 'crilayla:%s' % e))
                continue
        else:
            buf = data[off:off + (r.get('FileSize') or 0)].rstrip(b'\x00')
        rel = name.replace('\\', '/').lstrip('/')
        rel = ''.join(('_' if ch in '<>:"|?*' or ord(ch) < 32 else ch) for ch in rel)
        dst = os.path.join(outdir, *rel.split('/'))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, 'wb') as o:
            o.write(buf)
        n += 1
    print('extracted', n, 'bad', len(bad))
    for b in bad[:10]:
        print('  BAD', b)


if __name__ == '__main__':
    main()
