#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PFS0(NSP) 逐块直拷拆分器 —— 规避 hactool --pfs0dir 对 >1.7GB 成员写全零的问题。
用法: python split_pfs0.py <nsp> <outdir>
"""
import os, struct, sys

def split(nsp, outdir):
    os.makedirs(outdir, exist_ok=True)
    with open(nsp, 'rb') as f:
        magic = f.read(4)
        assert magic == b'PFS0', magic
        count, strsize, _ = struct.unpack('<3I', f.read(12))
        entries = []
        for _ in range(count):
            off, size, nameoff, _r = struct.unpack('<QQII', f.read(24))
            entries.append([off, size, nameoff])
        strtab = f.read(strsize)
        data_start = 0x10 + count * 0x18 + strsize
        out = []
        for off, size, nameoff in entries:
            end = strtab.find(b'\x00', nameoff)
            name = strtab[nameoff:end].decode('utf-8')
            f.seek(data_start + off)
            dst = os.path.join(outdir, name)
            left = size
            with open(dst, 'wb') as w:
                while left:
                    chunk = f.read(min(8 << 20, left))
                    if not chunk:
                        break
                    w.write(chunk)
                    left -= len(chunk)
            out.append((name, size))
            print(f'{name}\t{size}')
    return out

if __name__ == '__main__':
    split(sys.argv[1], sys.argv[2])
