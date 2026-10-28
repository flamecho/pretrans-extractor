#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""uf_render.py —— 恋愛番長2 `font/0`（UF_ 自研字体）字形渲染/探查工具

用法:
  python scripts/uf_render.py 8448              # 按 cp932 码位渲染一个字形（ASCII art）
  python scripts/uf_render.py З                 # 也可以直接给字符
  python scripts/uf_render.py --slots           # 渲染 16 个数字槽
  python scripts/uf_render.py --info            # 打印字体结构摘要

已确证（2026-10-20）
  * 0x04 u32 = 7110 字形数；0x14/0x18/0x1C = 三段表偏移（32 / 0x494 / 0xE2C4）
  * 0x20 起 95 条 (u32 code_lo, u32 code_hi, u32 first_glyph)；hi 开区间
      → glyph = first_glyph + (code - code_lo)，95 段首尾相接、合计 7110，零空隙（已校验）
  * 0x494 起 7110 条 (u16 A, u16 size, u32 offset)；offset 累计 = 1,251,830 = 文件尾
      A = 0x1D00 | advance_width   ← 已用「半角空格=9 / 全角空格=21 / 数字 15..19」证实
  * 字形高 29 行（空格 = W*29 像素，两例精确吻合）
  * 像素流：b < 0x80 = 2 px（4bpp，高低半字节）；b >= 0x80 = 2 字节 token，计数在第 2 字节
      ⇒ 「０」可完整还原成圆角矩形；复杂字形仍每 token 漂移 ~1 px，token 集未定稿（见 --info）

未解：0x80/0xa0/0xb0/0xf0 四类的精确语义（是否 14bit/对齐行首/0px 指令）。
      下一步：拿「ー」「一」这类单笔画字形做最小反例，一次只定一类。
"""
import sys, struct, os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

HOME = os.environ.get('VNTRANS_HOME', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONT = os.environ.get('UF_FONT', os.path.join(HOME, '_work_koibann2', 'cpk', 'font', '0'))

SLOTS = ['8443', '8444', '8448', '8450', '8451', '8452', '8453', '8454',
         '8457', '8458', '845f', '8471', '8472', '847e', '8484', '8490']


class Font:
    def __init__(self, path=FONT):
        self.d = open(path, 'rb').read()
        assert self.d[:3] == b'UF_', 'not UF_ font'
        self.n = struct.unpack_from('<I', self.d, 4)[0]
        self.tbl, self.rec, self.dat = 0x20, 0x494, 0xE2C4
        self.blocks = [struct.unpack_from('<III', self.d, self.tbl + 12 * i) for i in range(95)]

    def gid(self, code):
        for lo, hi, fg in self.blocks:
            if lo <= code < hi:
                return fg + (code - lo)
        return None

    def raw(self, code):
        g = self.gid(code)
        if g is None:
            return None
        A, sz, off = struct.unpack_from('<HHI', self.d, self.rec + 8 * g)
        return A & 0xff, self.d[self.dat + off:self.dat + off + sz], g

    def pixels(self, code, mode='skip'):
        r = self.raw(code)
        if not r:
            return None, None
        W, dd, _ = r
        px, i = [], 0
        while i + 1 < len(dd):
            b = dd[i]
            if b < 0x80:
                px.append(b >> 4); px.append(b & 15); i += 1
            elif mode == 'rowalign' and b >= 0xe0:
                px.extend([0] * ((-len(px)) % W)); i += 2
            else:
                px.extend([0] * dd[i + 1]); i += 2
        return W, px

    def art(self, code, mode='skip', H=29, width=None):
        W, px = self.pixels(code, mode)
        if W is None:
            return '(无此码位)'
        W = width or W
        out = []
        for r in range(H):
            row = px[r * W:(r + 1) * W]
            if len(row) < W:
                row += [0] * (W - len(row))
            out.append(''.join('#' if v >= 9 else ('*' if v >= 6 else ('+' if v >= 3 else ('.' if v else ' '))) for v in row))
        return '\n'.join(out)

    def info(self):
        L = ['UF_ font: %s' % FONT, '  glyphs=%d  blocks=%d  data=0x%X' % (self.n, len(self.blocks), self.dat)]
        L.append('  advance: sp=9  全角sp=21  ０-９=%s' % [self.raw(0x824f + i)[0] for i in range(10)])
        return '\n'.join(L)


def main():
    f = Font()
    a = sys.argv[1:]
    if not a or a[0] == '--info':
        print(f.info()); return
    if a[0] == '--slots':
        for s in SLOTS:
            c = int(s, 16)
            W, dd, g = f.raw(c)
            print('=== %#06x %s  g%d  W=%d  size=%d' % (c, bytes.fromhex(s).decode('cp932'), g, W, len(dd)))
            print(f.art(c))
        return
    arg = a[0]
    code = int(arg, 16) if all(ch in '0123456789abcdefABCDEF' for ch in arg) else ord(arg)
    print(f.art(code))


if __name__ == '__main__':
    main()
