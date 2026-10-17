#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""STORM LOVER V (PSV PCSG00735) —— 资源解压工具（2026-10-11）。

★ 关键逆向结论：**容器内资源 = 普通 gzip/deflate**
  - `union.cpk`：type-A 条目段4 = `[MAP 头 + 坐标表][描述符(1,0x10,csize,0,usize)][gzip 流]`；
    1397/2406 条含 gzip，解压后为 **1024×512 等、8bpp 灰度** 的纹理（H 恒为 512 的倍数）。
  - `pr.bin`(6.4MB)：`[0..0xef0 头][63 个 gzip 流]`，每流解压 524288B = 1024×512 8bpp
    （スクリーントーン/网纹图案）。
  - `lt.bin`(2.3MB)：**非 gzip、非压缩**（熵 2.3-4.0、仅 150 种字节值、零占 43%）→ 结构化数值表，
    头 `u32@0x404 = 0x2420(9248)`，疑似字形轮廓/度量表（未解）。

用法：
  python stormlover_assets.py union <union.cpk> <出目录> [条目名...]
  python stormlover_assets.py pr    <pr.bin>    <出目录>
"""
import os, sys, struct, zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def gunzip_blocks(data, cap=1 << 27):
    """扫出 data 中所有 gzip 流并解压 → [(offset, decompressed_bytes), ...]"""
    out = []
    i = 0
    while True:
        k = data.find(b'\x1f\x8b\x08', i)
        if k < 0:
            break
        try:
            o = zlib.decompressobj(31)
            r = o.decompress(data[k:], cap)
            out.append((k, r))
        except Exception:
            pass
        i = k + 1
    return out


def union_decompress(cpk_path, outdir, names=None):
    from cpk import CPK
    os.makedirs(outdir, exist_ok=True)
    c = CPK(cpk_path)
    n = 0
    for e in c.entries:
        if names and e['name'] not in names:
            continue
        d = c.raw(e)
        k = d.find(b'\x1f\x8b\x08')
        if k < 0:
            continue
        try:
            r = zlib.decompressobj(31).decompress(d[k:], 1 << 27)
        except Exception:
            continue
        with open(os.path.join(outdir, e['name'] + '.bin'), 'wb') as f:
            f.write(r)
        n += 1
    print('union: 解压', n, '条 ->', outdir)


def pr_decompress(pr_path, outdir):
    os.makedirs(outdir, exist_ok=True)
    d = open(pr_path, 'rb').read()
    blocks = gunzip_blocks(d)
    for i, (off, r) in enumerate(blocks):
        with open(os.path.join(outdir, 'pr_%02d_%x.bin' % (i, off)), 'wb') as f:
            f.write(r)
    print('pr:', len(blocks), '个流 ->', outdir)


if __name__ == '__main__':
    what, src, out = sys.argv[1], sys.argv[2], sys.argv[3]
    if what == 'union':
        union_decompress(src, out, sys.argv[4:] or None)
    elif what == 'pr':
        pr_decompress(src, out)
    else:
        print(__doc__)
