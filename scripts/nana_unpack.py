#!/usr/bin/env python3
"""nana_unpack.py -- [PS2-JP] NANA -ナナ- STORY/ALLSC.NKP 解包（Konami NKP 嵌套）。

ALLSC.NKP(NKP) -> 1092 x <名>.nkp(NKP) -> *.cg（cp932 明文命令脚本）/ *.txt / *.bin
用法: python scripts/nana_unpack.py <ALLSC.NKP> <outdir>
"""
import os
import struct
import sys


def nkp_entries(d, base=0, limit=None):
    assert d[base:base + 4] == b'NKP\x1a', 'not NKP'
    total, _, cnt = struct.unpack_from('<3I', d, base + 4)
    ents = []
    for i in range(cnt):
        no, do = struct.unpack_from('<2I', d, base + 0x10 + i * 8)
        e = d.find(b'\x00', base + no)
        name = d[base + no:e].decode('latin1')
        ents.append((do, name))
    ents.sort()
    out = []
    for i, (off, name) in enumerate(ents):
        end = ents[i + 1][0] if i + 1 < len(ents) else (limit or total)
        out.append((name, d[off:end]))
    return out


def main():
    src, outdir = sys.argv[1], sys.argv[2]
    d = open(src, 'rb').read()
    subs = nkp_entries(d)
    os.makedirs(outdir, exist_ok=True)
    n_cg = 0
    for name, blob in subs:
        base = name[:-4]
        try:
            inner = nkp_entries(blob, 0, len(blob))
        except AssertionError:
            print('!! not nkp', name, len(blob))
            continue
        for iname, data in inner:
            if iname.lower().endswith('.cg'):
                p = os.path.join(outdir, base + '_' + iname)
                open(p, 'wb').write(data)
                n_cg += 1
    print('subs', len(subs), 'cg', n_cg)


if __name__ == '__main__':
    main()
