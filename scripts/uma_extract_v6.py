import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
# -*- coding: utf-8 -*-
"""冬園サクリフィス [NS-JP] 文本提取 v6（按角色号/台词边界分行）

单位定义（= 引擎「一次点击」）：
    0x00 作者断行
  + 台词收尾 `」` 且其后不是 `「`（这一句说完了，说话人该换/转旁白）
  = 18,894 个单位；与脚本 `63 06`（设说话人）记录数 **18,839** 相差 55（0.29%）

字体侧佐证：单位宽度的中位数 50 半角单位（25 字），最长 306（153 字）；
窗口 `maxRow` 行、每行 41 全角字（TT_NewCezanne-DB advance 全角 1000 / ASCII 500，等宽），
所以 306/82 ≈ 3.7 行 ≤ maxRow，自洽。

不做任何「按字数拆」的处理。行首 U+3000 剥掉（引擎 RemoveZenkakuSpaceAfterNewLine 行为）。
"""
CHART = os.path.join(VNTRANS_HOME, '_w_wgs/chartable.bin')
ROOT = r'<本地路径>'
OUT = os.path.join(VNTRANS_HOME, '提取结果/[NS-JP]冬園サクリフィス.txt')
HEROINE = 'レティシア'

T = open(CHART, 'rb').read().decode('utf-8')


def load(fn):
    d = open(ROOT + fn, 'rb').read()
    assert d[:4] == b'UTXT', d[:4]
    off = int.from_bytes(d[12:16], 'little')
    out, i = [], off
    while i < len(d):
        b = d[i]
        if b == 0:
            out.append('\n'); i += 1
        elif b < 0x80:
            out.append(T[b - 1]); i += 1
        else:
            out.append(T[d[i + 1] + 128 * (b - 0x81) + 127]); i += 2
    return ''.join(out)


def split_units(text):
    """0x00 断行 + 台词收尾（」后不接「）= 新单位"""
    units = []
    for seg in text.split('\n'):
        cur = ''
        n = len(seg)
        for i, ch in enumerate(seg):
            cur += ch
            if ch == '」' and i + 1 < n and seg[i + 1] != '「':
                units.append(cur); cur = ''
        if cur:
            units.append(cur)
    return units


def build(text):
    res = []
    for u in split_units(text):
        u = u.lstrip('\u3000')
        if not u.strip():
            continue
        res.append(u.replace('$', '').replace('%', HEROINE))
    return res


if __name__ == '__main__':
    talk = load('uma_talk_2.bytes')
    lines = build(talk)
    print('units %d / chars %d' % (len(lines), sum(map(len, lines))))
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('written')
