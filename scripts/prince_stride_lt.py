#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""プリンス・オブ・ストライド (PSV PCSG00491) —— lt.bin 字形图集渲染（2026-10-12）。

规格（实测，与 STORM LOVER 系列**不同**）：
  392 B/字形 = 28 行 × 14 B（4bpp，28×28 点阵）；**无头部**；**字形索引 == 游戏码**（0..3525）；
  文件 1,382,400 B = 392×3526 + 192 B 零填充 + 16 B 哈希。

用法：
  python prince_stride_lt.py <lt.bin> <out.png> code1 code2 ...        # 渲染指定码
  python prince_stride_lt.py <lt.bin> <out.png> --sheet 3456 3526      # 区间对照表
"""
import os
import sys

CELL, W, H, BPR = 392, 28, 28, 14


def glyph(lt, code):
    from PIL import Image
    off = code * CELL
    img = Image.new("L", (W, H), 255)
    px = img.load()
    for y in range(H):
        for x in range(W):
            b = lt[off + y * BPR + (x >> 1)]
            v = (b >> 4) if (x & 1) == 0 else (b & 15)
            px[x, y] = 255 - v * 17
    return img


def main():
    lt = open(sys.argv[1], "rb").read()
    out = sys.argv[2]
    args = sys.argv[3:]
    from PIL import Image, ImageDraw
    if args and args[0] == "--sheet":
        lo, hi = int(args[1]), int(args[2])
        codes = list(range(lo, hi))
        scale, cols = 8, 5
        cw, ch = W * scale + 10, H * scale + 26
        rows = (len(codes) + cols - 1) // cols
        sheet = Image.new("L", (cols * cw, rows * ch), 220)
        dr = ImageDraw.Draw(sheet)
        for i, c in enumerate(codes):
            r, q = divmod(i, cols)
            sheet.paste(glyph(lt, c).resize((W * scale, H * scale), Image.NEAREST),
                        (q * cw + 5, r * ch + 22))
            dr.text((q * cw + 5, r * ch + 6), str(c), fill=0)
        sheet.save(out)
    else:
        codes = [int(a) for a in args]
        scale = 10
        sheet = Image.new("L", (len(codes) * (W * scale + 10), H * scale + 26), 220)
        dr = ImageDraw.Draw(sheet)
        for i, c in enumerate(codes):
            sheet.paste(glyph(lt, c).resize((W * scale, H * scale), Image.NEAREST),
                        (i * (W * scale + 10) + 5, 22))
            dr.text((i * (W * scale + 10) + 5, 6), str(c), fill=0)
        sheet.save(out)
    print("saved", out)


if __name__ == "__main__":
    main()
