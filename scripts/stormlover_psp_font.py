#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""STORM LOVER 夏恋!!（PSP）—— lt.bin 自建位图字体渲染（2026-10-12）。

逆向结论（逐位置定值复元，经真实字形验证）：
  lt.bin = 字形图集，**18 × 18 px / 字形，4bpp（高半字节在前），9 B/行 → 162 B/字形**。
  字形索引 == 游戏码，从 0 起（验证：code566='一' 横线、code1335='口' 方框，渲染完全正确）。
  文件 = 3577 个完整字形（3577×162 = 579,474 B）+ 尾部 110 B 残余。
  与 PSV 版对照：PSV = 36×36 / 648 B（PSP 为其 1/2 尺寸 → 162×4 = 648 ✔ 同族）。

用法：
  python scripts/stormlover_psp_font.py sheet <lt.bin> <out.png> <c0> <c1> [--scale 6]
  python scripts/stormlover_psp_font.py text  <lt.bin> <code> [...]
"""
import sys

W = H = 18
GS = W * 4 // 8 * H          # 162 B/glyph
NGLYPH = 579474 // GS        # 3577


def load(path):
    with open(path, 'rb') as f:
        return f.read()


def nibble(data, base, x, y):
    b = data[base + y * (W // 2) + x // 2]
    return (b >> 4) if x % 2 == 0 else (b & 0xF)


def glyph_img(data, code, scale=1):
    from PIL import Image
    img = Image.new('L', (W, H), 255)
    px = img.load()
    base = code * GS
    for y in range(H):
        for x in range(W):
            if base + GS > len(data):
                break
            v = nibble(data, base, x, y)
            px[x, y] = 255 - v * 17
    if scale != 1:
        img = img.resize((W * scale, H * scale), Image.NEAREST)
    return img


def sheet(path, out, c0, c1, scale=6, cols=12):
    from PIL import Image, ImageDraw
    data = load(path)
    codes = list(range(c0, c1 + 1))
    cw, ch = W * scale, H * scale + 16
    rows = (len(codes) + cols - 1) // cols
    canvas = Image.new('L', (cols * (cw + 6) + 6, rows * (ch + 6) + 6), 220)
    dr = ImageDraw.Draw(canvas)
    for i, code in enumerate(codes):
        r, c = divmod(i, cols)
        ox = 6 + c * (cw + 6)
        oy = 6 + r * (ch + 6)
        canvas.paste(glyph_img(data, code, scale), (ox, oy))
        dr.text((ox + 2, oy + H * scale + 2), str(code), fill=0)
    canvas.save(out)
    print('saved', out, len(codes), 'glyphs')


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'sheet':
        sc = 6
        if '--scale' in sys.argv:
            sc = int(sys.argv[sys.argv.index('--scale') + 1])
        sheet(sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), sc)
    elif cmd == 'text':
        data = load(sys.argv[2])
        for code in [int(a) for a in sys.argv[3:]]:
            print('=== code', code, '===')
            for y in range(H):
                print(''.join(' .:-=+*#%@'[min(9, nibble(data, code * GS, x, y))] for x in range(W)))
