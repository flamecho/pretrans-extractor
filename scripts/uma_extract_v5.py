# -*- coding: utf-8 -*-
"""冬園サクリフィス [NS-JP] 文本提取 v5（引擎行复现）

链路（全部取证，无猜）：
 1. 容器 UTXT：+0x00 magic / +0x04 ver=1 / +0x0C 字符流绝对偏移
 2. 字符流：0x00=换行码 / 0x01-0x7F=chartable[b-1] / 0x81xx=chartable[trail+128*(lead-0x81)+127]
 3. 字体 TT_NewCezanne-DB（sharedassets0.assets → Font.m_FontData, 4.43 MB, upem=1000）：
       全角 advance 1000/1000 = 1.0 em；ASCII 500/1000 = 0.5 em  ⇒ 等宽
 4. 行宽容量：由 uma_event_range_2.txt 哨兵 19,258（全篇行数）反解 = 41 全角字（W=82 半角单位）；
       该容量下复现行数 19,266，误差 +8 / 0.04%
 5. 行头禁则：“追い出し”（行首若是 、。」… 等，把上一字一并推下去）

成行：0x00 切作者行 → 按容量折行 → 剥行首 U+3000（引擎 RemoveZenkakuSpaceAfterNewLine）
      → `$` 去壳 / `%` → レティシア
"""
import sys, unicodedata
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

CHART = os.path.join(VNTRANS_HOME, '_w_wgs/chartable.bin')
ROOT = r'<本地路径>'
OUT = os.path.join(VNTRANS_HOME, '提取结果/[NS-JP]冬園サクリフィス.txt')
HEROINE = 'レティシア'
ROW_W = 82                     # 半角单位 = 41 全角字

NO_START = set('、。，．・：；？！）〕］｝〉》」』】”’…‥ー―'
               'ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ')
NO_END = set('（〔［｛〈《「『【“‘')

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


def em(ch):
    """TT_NewCezanne-DB 实测：全角 1.0em / ASCII 0.5em"""
    return 2 if ord(ch) >= 0x2000 else 1


def wrap(s, W=ROW_W):
    out, cur, acc = [], [], 0
    for ch in s:
        c = em(ch)
        if acc + c <= W or not cur:
            cur.append(ch); acc += c
            continue
        if ch in NO_START:              # 行头禁则：上一字陪着一起下去
            moved = []
            while cur and len(moved) < 3:
                moved.insert(0, cur.pop())
                if moved[0] not in NO_START:
                    break
            if cur:
                out.append(''.join(cur))
                cur = moved + [ch]
                acc = sum(em(x) for x in cur)
            else:
                cur = moved + [ch]
                acc = sum(em(x) for x in cur)
            continue
        if cur[-1] in NO_END and len(cur) > 1:   # 行末禁则：开引号带下去
            last = cur.pop(); out.append(''.join(cur))
            cur, acc = [last, ch], em(last) + c
            continue
        out.append(''.join(cur)); cur, acc = [ch], c
    if cur:
        out.append(''.join(cur))
    return out


def build(talk):
    res = []
    for line in talk.split('\n'):
        if not line.strip():
            continue
        line = line.replace('$', '').replace('%', HEROINE)   # 先替换再排版（引擎顺序）
        for row in wrap(line):
            if row.strip():
                res.append(row)
    return res


if __name__ == '__main__':
    talk = load('uma_talk_2.bytes')
    rows = build(talk)
    print('rows %d / chars %d' % (len(rows), sum(map(len, rows))))
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(rows) + '\n')
    print('written')
