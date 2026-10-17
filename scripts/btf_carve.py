#!/usr/bin/env python3
"""btf_carve.py —— 从 INSTALL.BIN 中按 fileinfo.psb.m.json 的 umd_root 表切出成员文件。

用法: python scripts/btf_carve.py <INSTALL.BIN> <fileinfo.psb.m.json> <outdir> [成员名...]
表项语义: [?, size, offset]（3 元素，容器内偏移）或 [LBA, size]（2 元素，UMD 直读，跳过）。
"""
import json, os, sys

def main():
    body, js, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    want = sys.argv[4:]
    d = json.load(open(js, encoding='utf-8'))
    root = d['umd_root']
    fs = open(body, 'rb')
    os.makedirs(outdir, exist_ok=True)
    for name, v in root.items():
        if want and name not in want:
            continue
        if len(v) != 3:
            print('skip (umd direct)', name, v)
            continue
        _, size, off = v
        size = int(size); off = int(off)
        fs.seek(off)
        buf = fs.read(size)
        assert len(buf) == size, (name, len(buf), size)
        p = os.path.join(outdir, name.replace('/', os.sep))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(buf)
        print('%-24s %10d @%12d' % (name, size, off))

main()
