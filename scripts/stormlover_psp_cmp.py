#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""STORM LOVER 夏恋!!（PSP）—— 二级槽「字形 vs 候选字」比对图（人工目视定值）。

用法: python scripts/stormlover_psp_cmp.py <lt.bin> <out.png> <slotcode> <候选字...>
"""
import sys
from PIL import Image, ImageDraw, ImageFont

W = H = 18
GS = 162
FONT = r'C:\Windows\Fonts\msgothic.ttc'
S = 18          # 槽字形放大倍数
CS = 44         # 候选字渲染字号


def slot_img(data, code):
    im = Image.new('L', (W, H), 255)
    px = im.load()
    base = code * GS
    for y in range(H):
        for x in range(W):
            b = data[base + y * 9 + x // 2]
            v = (b >> 4) if x % 2 == 0 else (b & 0xF)
            px[x, y] = 255 - int(v * 255 / 9)
    return im.resize((W * S, H * S), Image.NEAREST)


def cand_img(ch, font):
    im = Image.new('L', (76, 76), 255)
    dr = ImageDraw.Draw(im)
    bb = dr.textbbox((0, 0), ch, font=font)
    dr.text(((76 - (bb[2] - bb[0])) // 2 - bb[0], (76 - (bb[3] - bb[1])) // 2 - bb[1]),
            ch, font=font, fill=0)
    return im


def main():
    data = open(sys.argv[1], 'rb').read()
    out, code = sys.argv[2], int(sys.argv[3])
    cands = sys.argv[4:]
    font = ImageFont.truetype(FONT, CS)
    lab = ImageFont.truetype(FONT, 16)
    cw = W * S
    n = len(cands)
    cv = Image.new('L', (cw + 12 + n * 84, max(cw, 96) + 24), 230)
    dr = ImageDraw.Draw(cv)
    cv.paste(slot_img(data, code), (6, 6))
    dr.text((6, cw + 8), 'slot %d' % code, font=lab, fill=0)
    for i, ch in enumerate(cands):
        ox = cw + 18 + i * 84
        cv.paste(cand_img(ch, font), (ox, 6))
        dr.text((ox + 28, cw + 8), ch, font=lab, fill=0)
    cv.save(out)
    print('saved', out)


if __name__ == '__main__':
    main()
