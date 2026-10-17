#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Vamwolf Cross† lt.bin 字形图集渲染。
规格（实测）：392 B/字形 = 28 行 × 14 B（4bpp，28×28）；索引 == 游戏码。
用法：
  python vamwolf_lt.py <lt.bin> <out.png> <code1> <code2> ...
  python vamwolf_lt.py <lt.bin> <out.png> --sheet <lo> <hi>
"""
import os
import sys

CELL, W, H, BPR = 392, 28, 28, 14
BASE = 0            # 若文件有头部，改这里
TH = int(os.environ.get('VW_TH', '8'))


def glyph(lt, code):
    from PIL import Image
    off = BASE + code * CELL
    img = Image.new("L", (W, H), 255)
    px = img.load()
    for y in range(H):
        for x in range(W):
            b = lt[off + y * BPR + (x >> 1)]
            v = (b >> 4) if (x & 1) == 0 else (b & 15)
            px[x, y] = 0 if v >= TH else 255
    return img


def main():
    lt = open(sys.argv[1], "rb").read()
    out = sys.argv[2]
    args = sys.argv[3:]
    from PIL import Image, ImageDraw
    if args and args[0] == "--grid":
        cols = int(args[1])
        codes = [int(a) for a in args[2:]]
        scale = int(os.environ.get("VW_SC", "9"))
        cw, ch = W * scale + 10, H * scale + 26
        rows = (len(codes) + cols - 1) // cols
        sheet = Image.new("L", (cols * cw, rows * ch), 225)
        dr = ImageDraw.Draw(sheet)
        for i, c in enumerate(codes):
            r, q = divmod(i, cols)
            sheet.paste(glyph(lt, c).resize((W * scale, H * scale), Image.NEAREST),
                        (q * cw + 5, r * ch + 22))
            dr.text((q * cw + 5, r * ch + 6), str(c), fill=0)
        sheet.save(out)
    elif args and args[0] == "--sheet":
        lo, hi = int(args[1]), int(args[2])
        codes = list(range(lo, hi))
        scale, cols = 7, 8
        cw, ch = W * scale + 8, H * scale + 24
        rows = (len(codes) + cols - 1) // cols
        sheet = Image.new("L", (cols * cw, rows * ch), 225)
        dr = ImageDraw.Draw(sheet)
        for i, c in enumerate(codes):
            r, q = divmod(i, cols)
            sheet.paste(glyph(lt, c).resize((W * scale, H * scale), Image.NEAREST),
                        (q * cw + 4, r * ch + 20))
            dr.text((q * cw + 4, r * ch + 4), str(c), fill=0)
        sheet.save(out)
    else:
        codes = [int(a) for a in args]
        scale = 12
        sheet = Image.new("L", (len(codes) * (W * scale + 12), H * scale + 26), 225)
        dr = ImageDraw.Draw(sheet)
        for i, c in enumerate(codes):
            sheet.paste(glyph(lt, c).resize((W * scale, H * scale), Image.NEAREST),
                        (i * (W * scale + 12) + 6, 22))
            dr.text((i * (W * scale + 12) + 6, 6), str(c), fill=0)
        sheet.save(out)
    print("saved", out)


if __name__ == "__main__":
    main()
