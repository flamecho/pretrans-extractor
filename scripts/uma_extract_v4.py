# -*- coding: utf-8 -*-
"""冬園サクリフィス [NS-JP] UTXT 文本提取（v4）

结构（全部由代码/引擎字段取证）：
  容器 UTXT: +0x00 'UTXT' / +0x04 ver=1 / +0x08 常量 / +0x0C 字符流绝对偏移
  字符流   : 0x00=换行码 / 0x01-0x7F=chartable[b-1] / 0x81xx=chartable[trail+128*(lead-0x81)+127]
  行       : 0x00 是作者断行（引擎 RemoveZenkakuSpaceAfterNewLine 会剥掉其后的 U+3000）
  第二层   : 引擎 ReadTextLinesAsync 在加载时把行再按显示宽度折成 row，TextDisp 用
             maxRow / rowWordCount / dispWordCounts 分页；uma_event_range 的 0..19258 就是
             row 序号。row 宽度按 19,258 处反推 ≈ 40 全角字 ⇒ 只对超过该宽度的行做折行。

成行：按 0x00 切 -> 剥行首 U+3000 -> $ 去壳 / % -> レティシア
      -> 仅当该行宽 > ROW_W 时按 ROW_W 禁则折行（不合并、不按括号切）
"""
import unicodedata
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

CHART = os.path.join(VNTRANS_HOME, '_w_wgs/chartable.bin')
ROOT = r'<本地路径>'
OUT = os.path.join(VNTRANS_HOME, '提取结果/[NS-JP]冬園サクリフィス.txt')
HEROINE = 'レティシア'
ROW_W = 80          # 半角单位 = 40 全角字（由 uma_event_range 哨兵 19,258 反推）

T = open(CHART, 'rb').read().decode('utf-8')

NO_START = set('、。，．・：；？！゛゜ヽヾゝゞ々ー―‐／＼～∥｜…‥’”）〕］｝〉》」』】'
               'ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ')
NO_END = set('‘“（〔［｛〈《「『【')


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


def cw(ch):
    return 2 if unicodedata.east_asian_width(ch) in 'WF' else 1


def width(s):
    return sum(cw(c) for c in s)


def wrap(s, W=ROW_W):
    """按显示宽度 W 折行，禁则处理；返回列表"""
    out, cur, acc = [], [], 0
    for ch in s:
        c = cw(ch)
        if acc + c > W and cur:
            if ch in NO_START:                       # 行首禁则：跟着上一行走（允许溢出 1 字）
                cur.append(ch); out.append(''.join(cur))
                cur, acc = [], 0
                continue
            if cur[-1] in NO_END and len(cur) > 1:   # 行末禁则：把开引号带下去
                last = cur.pop(); out.append(''.join(cur))
                cur, acc = [last, ch], cw(last) + c
                continue
            out.append(''.join(cur)); cur, acc = [ch], c
        else:
            cur.append(ch); acc += c
    if cur:
        out.append(''.join(cur))
    return out


def build(talk):
    lines = []
    for row in talk.split('\n'):
        row = row.lstrip('\u3000')
        if not row.strip():
            continue
        row = row.replace('$', '').replace('%', HEROINE)
        lines.extend(wrap(row) if width(row) > ROW_W else [row])
    return lines


if __name__ == '__main__':
    talk = load('uma_talk_2.bytes')
    lines = build(talk)
    print('lines', len(lines), 'chars', sum(map(len, lines)))
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
