# -*- coding: utf-8 -*-
"""STORM LOVER V (PCSG00735) 字形图集读取器 —— lt.bin

★ 关键结论（2026-10-11 逆向后确认，可复用于同引擎作品）：
  USRDIR/lt.bin = 游戏自建位图字体的「字形图集」。
  布局：每字形 648 字节 = 36 行 × 18 字节；18 字节 = 36 px（4bpp 打包，2 像素/字节）。
        字形索引 == 游戏字符码（即 stormlover_charset.CHARSET 的下标），从 0 开始。
  文件大小 2,324,480 = 648 × 3587.16 ⇒ 覆盖 code 0..3586（共 3587 个字形）。
  自检：`glyph(0x100)` 起是 JIS 記号区（希腊/西里尔/制表符/★○●→←↑↓/ＡＢＣ…）；
        CHARSET.index('あ')=209 → glyph 209 == 「あ」字形。

  用法：
    from stormlover_font import glyph_bbox, render, glyph_bytes
    render(3466).save(...)          # 渲染某码字形为 PIL Image
"""
import os

LT_BIN = os.environ.get('SL_LTBIN', '')
CELL = 648          # bytes / glyph
GW, GH, BPP = 36, 36, 4


def load(path=None):
    p = path or LT_BIN
    if not p:
        for c in ('_src_stormlover/dec_app/USRDIR/lt.bin',
                  'lt.bin'):
            if os.path.exists(c):
                p = c; break
    return open(p, 'rb').read()


def glyph_bytes(data, code):
    """返回该码的 648 字节原始字形数据。"""
    off = code * CELL
    return data[off:off + CELL]


def decode_pixels(blk):
    """4bpp 打包 → 0..15 像素值列表（36×36=1296）。"""
    out = []
    for b in blk:
        out.append((b >> 4) & 15)
        out.append(b & 15)
    return out


def render(code, data=None):
    """渲染 code 的字形为 36×36 灰度 PIL Image（0..255）。"""
    from PIL import Image
    data = data if data is not None else load()
    px = bytes(v * 17 for v in decode_pixels(glyph_bytes(data, code))[:GW * GH])
    return Image.frombytes('L', (GW, GH), px)


def max_code(data=None):
    data = data if data is not None else load()
    return len(data) // CELL


if __name__ == '__main__':
    d = load()
    print('lt.bin size =', len(d), '  glyphs =', max_code(d), '(code 0..%d)' % (max_code(d) - 1))
