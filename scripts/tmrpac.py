#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TMR-Hiro ADV System 系 `.pac` 容器解包（PC / クレイジー★ラビッツ 実測）

格式（2026-10-30 由 srp/se/sse/grd/mus/vic 六个包交叉验证）：

  文件头 7 字节
    +0x00  u16  entry_count
    +0x02  u8   name_width      ← 名字字段宽度（逐包不同：srp=16 / se,sse=7 / grd=17 / mus=5 / vic=12）
    +0x03  u24  toc_end        (小端；= 7 + (name_width+8)*count，数据区起点)
    +0x06  u8   0x00
  条目 (name_width + 8) 字节 × count（紧跟文件头）
    +0x00  char name[name_width]   NUL 补齐
    +N     u32  offset             相对 toc_end
    +N+4   u32  size
  数据区 @ toc_end：条目数据**不压缩**（se.pac 内 1500 个 `OggS`、grd.pac 512 个 `PNG`）

校验：`7 + (name_width+8)*count == toc_end`，且 `offset[k] == Σ size[0..k-1]`，`toc_end + Σsize == 文件长`。
三个等式对六个包（共 12,241 条目）全部成立 ⇒ 容器层已闭合。

用法：
  python scripts/tmrpac.py list    <x.pac>
  python scripts/tmrpac.py extract <x.pac> <outdir> [--filter 前缀]
"""
import os
import struct
import sys

HDR = 7


def read_pac(path):
    d = open(path, "rb").read()
    count, = struct.unpack_from("<H", d, 0)
    nw = d[2]
    toc_end = d[3] | (d[4] << 8) | (d[5] << 16)
    ent = nw + 8
    rows = []
    p = HDR
    for _ in range(count):
        name = d[p:p + nw].split(b"\0")[0].decode("ascii", "replace")
        off, size = struct.unpack_from("<II", d, p + nw)
        rows.append((name, off, size))
        p += ent
    assert p == toc_end, f"TOC 不闭合: 7+{ent}*{count}={p:#x} != {toc_end:#x}"
    # 累积校验
    acc = 0
    for name, off, size in rows:
        assert off == acc, f"{name} offset 不连续: {off} != {acc}"
        acc += size
    assert toc_end + acc == len(d), f"数据区不闭合: {toc_end + acc:#x} != {len(d):#x}"
    return d, toc_end, rows, nw


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    cmd, src = sys.argv[1], sys.argv[2]
    d, toc_end, rows, nw = read_pac(src)
    print(f"[i] {os.path.basename(src)}  {len(d):,} B  entries={len(rows)}  "
          f"toc_end={toc_end:#x}  nameW={nw}")
    if cmd == "list":
        for name, off, size in rows:
            print(f"  {name:16s} {off:10d} {size:10d}")
        return
    out = sys.argv[3]
    pref = ""
    for i, a in enumerate(sys.argv):
        if a == "--filter":
            pref = sys.argv[i + 1]
    os.makedirs(out, exist_ok=True)
    n = 0
    for name, off, size in rows:
        if pref and not name.startswith(pref):
            continue
        with open(os.path.join(out, name), "wb") as f:
            f.write(d[toc_end + off:toc_end + off + size])
        n += 1
    print(f"[i] 导出 {n} 个 → {out}")


if __name__ == "__main__":
    main()
