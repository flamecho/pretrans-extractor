#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""いざ、出陣！恋戦 data.cpk → scenario/*.ks（内容锚定版）

CPK 表头两处与本作不符（2026-10-18 实证）：
  * FileOffset 列与行存在 ±1 行错位 ⇒ 不信任列，改用「数据区自扫描 + 内容内 '; <name>.ks' 注释」锚定身份
  * CRILAYLA 头 u32@8 不是明文总长（比真实内容长），故**按码流耗尽自然终止**解码
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from izasen_cpk import CPK932


def crilayla(block, cap=None):
    usize, csize = struct.unpack_from('<II', block, 8)
    src = block[16:16 + csize]
    pre = block[16 + csize:16 + csize + 0x100]
    if cap is None:
        cap = max(usize, 0x100)
    buf = bytearray(cap + 0x100)
    sp = len(src) - 1
    dp = len(buf) - 1
    bc = 0
    bd = 0

    def gb(k):
        nonlocal sp, bc, bd
        while bc < k:
            if sp < 0:
                raise EOFError
            bd = ((bd << 8) | src[sp]) & 0xFFFFFFFF
            sp -= 1
            bc += 8
        r = (bd >> (bc - k)) & ((1 << k) - 1)
        bc -= k
        return r

    try:
        while dp >= 0:
            if gb(1):
                off = gb(13) + 3
                cnt = gb(8) + 3
                for _ in range(cnt):
                    if dp < 0 or dp + off >= len(buf):
                        raise EOFError
                    buf[dp] = buf[dp + off]
                    dp -= 1
            else:
                buf[dp] = gb(8)
                dp -= 1
    except EOFError:
        pass
    return bytes(pre) + bytes(buf[dp + 1:])


NAME_RE = re.compile(rb'^;\s*([^\r\n]+?\.ks)\s*\r?\n')


def main():
    cpk, outdir = sys.argv[1], sys.argv[2]
    c = CPK932(cpk)
    data = open(cpk, 'rb').read()
    t, _ = c._read_utf_at(c.TocOffset)
    rows = t.rows
    offs = sorted({(r.get('FileOffset') or 0) for r in rows})
    by_off = {}
    for r in rows:
        by_off.setdefault(r.get('FileOffset') or 0, []).append(r)
    n = 0
    fail = 0
    names = []
    for o in offs:
        if o <= 0 or o >= len(data):
            continue
        if data[o:o + 8] == b'CRILAYLA':
            try:
                buf = crilayla(data[o:o + 8 + 0x1000])
            except Exception:
                fail += 1
                continue
        elif data[o:o + 1] == b';':
            fs = max((r.get('FileSize') or 0) for r in by_off[o])
            buf = data[o:o + fs].rstrip(b'\x00')
        else:
            continue
        m = NAME_RE.match(buf)
        if not m:
            fail += 1
            continue
        name = m.group(1).decode('cp932', 'replace')
        names.append(name)
        dst = os.path.join(outdir, name.replace('/', '_'))
        os.makedirs(outdir, exist_ok=True)
        with open(dst, 'wb') as fh:
            fh.write(buf)
        n += 1
    print('blocks ok', n, 'fail', fail, 'unique offsets', len(offs))
    print('unique names', len(set(names)))


if __name__ == '__main__':
    main()
