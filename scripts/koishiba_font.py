#!/usr/bin/env python3
"""koishiba_font.py —— 恋は校則に縛られない！（PSP / Vridge・D3P 系）lt.bin 字形渲染。

逆向结论（2026-10-19）：
  lt.bin = 4bpp 位图字形图集，**16 × 16 px / 字形，8 B/行 → 128 B/字形**，索引 == 游戏码（0 起）。
  （450560 B / 128 = 3520 个字形；锚字验证：code566='一' 横线、code1335='口' 方框 渲染正确。）
  基础区 0..3455 ＝ cp932 原码序（同 D3P 其他作）；3456..3519 ＝ 本作自用字形槽。

用法：
  python scripts/koishiba_font.py sheet <lt.bin> <out.png> <c0> <c1> [--scale 6]
  python scripts/koishiba_font.py text  <lt.bin> <code> [...]
"""
import sys

W = H = 16
GS = W // 2 * H            # 128 B/glyph


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
            px[x, y] = 255 - nibble(data, base, x, y) * 17
    if scale != 1:
        img = img.resize((W * scale, H * scale), Image.NEAREST)
    return img


def sheet(path, out, c0, c1, scale=6, cols=8):
    from PIL import Image, ImageDraw
    data = load(path)
    n = c1 - c0 + 1
    rows = (n + cols - 1) // cols
    cw, ch = W * scale + 6, H * scale + 4 + 12
    img = Image.new('RGB', (cols * cw, rows * ch), 'white')
    d = ImageDraw.Draw(img)
    for i, code in enumerate(range(c0, c1 + 1)):
        cx, cy = (i % cols) * cw + 3, (i // cols) * ch + 2
        img.paste(glyph_img(data, code, scale), (cx, cy))
        d.text((cx, cy + H * scale + 1), str(code), fill='black')
    img.save(out)
    print('saved', out, img.size)


def main():
    cmd = sys.argv[1]
    if cmd == 'sheet':
        path, out, c0, c1 = sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
        sc = 6
        if '--scale' in sys.argv:
            sc = int(sys.argv[sys.argv.index('--scale') + 1])
        sheet(path, out, c0, c1, sc)
    elif cmd == 'text':
        data = load(sys.argv[2])
        for a in sys.argv[3:]:
            code = int(a)
            print('=== code', code, 'base', code * GS)
            for y in range(H):
                row = ''.join('%x' % nibble(data, code * GS, x, y) for x in range(W))
                print(row)
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
