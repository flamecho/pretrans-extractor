# -*- coding: utf-8 -*-
"""按 TT_NewCezanne-DB 的真实 advance 复现引擎折行。

字体实测（_w_wgs/TT_NewCezanne-DB.ttf, head.unitsPerEm=1000）:
  全角（和文/記号/全角空白）advance = 1000/1000 = 1.0 em
  半角（ASCII）        advance =  500/1000 = 0.5 em
⇒ 等宽字体，等价于「全角=2、半角=1」的定宽折行。

宽容量 W（半角单位）由 uma_event_range_2.txt 哨兵 19,258（全篇行数）反解。
"""
import sys
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
from uma_boxes import load

ROW_W = 82          # 半角单位 = 41 全角字

# 行头禁则：不得出现在行首（TMP 行头禁则 / 日本語禁則）
NO_START = set('、。，．・：；？！）〕］｝〉》」』】”’、。ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶー―…‥')
NO_END = set('（〔［｛〈《「『【“‘')


def em(c):
    return 2 if ord(c) >= 0x2000 else 1


def wrap(s, W=ROW_W, hang=True):
    """返回 [(row_text, break_char)]，hang=True 时行头禁则字符吊在上一行末。"""
    out, cur, acc = [], [], 0
    for ch in s:
        c = em(ch)
        if acc + c > W and cur:
            if hang and ch in NO_START:
                cur.append(ch); out.append(''.join(cur))
                cur, acc = [], 0
                continue
            if cur[-1] in NO_END and len(cur) > 1:
                last = cur.pop(); out.append(''.join(cur))
                cur, acc = [last, ch], em(last) + c
                continue
            out.append(''.join(cur)); cur, acc = [ch], c
        else:
            cur.append(ch); acc += c
    if cur:
        out.append(''.join(cur))
    return out


def count(text, W=ROW_W, hang=True):
    n = 0
    for line in text.split('\n'):
        if line:
            n += len(wrap(line, W, hang))
    return n


if __name__ == '__main__':
    s = load('uma_talk_2.bytes').replace('%', 'レティシア').replace('$', '')
    s2 = s.replace('\x00', '\n')
    print('target 19258')
    for W in range(76, 90):
        for hang in (True, False):
            print('W%2d hang=%-5s %6d' % (W, hang, count(s2, W, hang)))
