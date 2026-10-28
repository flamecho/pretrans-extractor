#!/usr/bin/env python3
"""glyph_pick.py —— 在「语境候选字」之间做字形比对（仅用于验证假设，勿当 OCR 用）。

用法:
  python scripts/glyph_pick.py <lt.bin> <code> <候选字...>
输出：每个候选的相关系数（越大越像），并给出排序。
"""
import sys

sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from koishiba_font import load, nibble, W, H  # noqa: E402

GS = 128


def atlas_bits(data, code, th):
    return [[1 if nibble(data, code * GS, x, y) >= th else 0 for x in range(W)] for y in range(H)]


def ref_bits(ch, size=16):
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype(r'C:\Windows\Fonts\msgothic.ttc', size)
    img = Image.new('L', (size, size), 255)
    ImageDraw.Draw(img).text((0, 0), ch, font=f, fill=0)
    return [[1 if img.getpixel((x, y)) < 128 else 0 for x in range(size)] for y in range(size)]


def score(a, b):
    best = -1
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            inter = union = 0
            for y in range(H):
                for x in range(W):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < W:
                        av, bv = a[y][x], b[yy][xx]
                    else:
                        av, bv = a[y][x], 0
                    if av and bv:
                        inter += 1
                    if av or bv:
                        union += 1
            if union:
                s = inter / union
                best = max(best, s)
    return best


def main():
    path, code = sys.argv[1], int(sys.argv[2])
    cands = sys.argv[3:]
    data = load(path)
    a = atlas_bits(data, code, 6)
    res = []
    for ch in cands:
        r = ref_bits(ch)
        res.append((max(score(a, r), score(a, [[1 - v for v in row] for row in r])), ch))
    res.sort(reverse=True)
    print(code, ' '.join('%s:%.3f' % (c, s) for s, c in res))


if __name__ == '__main__':
    main()
