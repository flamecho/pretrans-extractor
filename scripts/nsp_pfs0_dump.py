#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""纯 Python 解析 PFS0(NSP) 并导出条目（hactool 吃不了 CJK 路径）。"""
import os, struct, sys, shutil

def parse(p, outdir):
    os.makedirs(outdir, exist_ok=True)
    with open(p, 'rb') as f:
        hdr = f.read(0x10000)
        assert hdr[:4] == b'PFS0', hdr[:4]
        cnt, strtab, _, _ = struct.unpack('<IIII', hdr[4:20])
        ent = hdr[0x10:0x10 + cnt * 0x18]
        names = hdr[0x10 + cnt * 0x18:0x10 + cnt * 0x18 + strtab]
        base = 0x10 + cnt * 0x18 + strtab
        out = []
        for i in range(cnt):
            o, sz, off, pad = struct.unpack('<QQII', ent[i * 0x18:(i + 1) * 0x18])
            nm = names[o:names.index(b'\0', o)].decode()
            dst = os.path.join(outdir, nm)
            f.seek(base + off)
            left = sz
            with open(dst, 'wb') as g:
                while left > 0:
                    b = f.read(min(1 << 22, left))
                    if not b:
                        break
                    g.write(b)
                    left -= len(b)
            print(nm, sz, '->', dst, flush=True)
            out.append(dst)
        return out


if __name__ == '__main__':
    parse(sys.argv[1], sys.argv[2])
