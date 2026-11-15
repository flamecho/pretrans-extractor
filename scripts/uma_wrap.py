# -*- coding: utf-8 -*-
"""推定引擎显示换行：0x00 强制断行 + 定宽自动折行（禁则处理），
以 uma_event_range_2.txt 的哨兵值 19258（全篇显示行数）为校验目标搜索行宽。"""
import unicodedata

# 行頭禁则（不得出现在行首）
NO_START = set('、。，．・：；？！゛゜ヽヾゝゞ々ー―‐／＼～∥｜…‥’”）〕］｝〉》」』】、。'
               'ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ')
# 行末禁则（不得出现在行尾）
NO_END = set('‘“（〔［｛〈《「『【')


def w(ch):
    if ch in '\u3000\u30fb':
        return 2
    return 2 if unicodedata.east_asian_width(ch) in 'WF' else 1


def wrap_line(s, W):
    """把一行（已按 0x00 切开）按宽 W（半角单位）折行，禁则处理"""
    out, cur, curw = [], [], 0
    for ch in s:
        cw = w(ch)
        if curw + cw > W and cur:
            # 行首禁则：把上一个字符挤下来
            if ch in NO_START:
                cur.append(ch); curw += cw
                out.append(''.join(cur)); cur, curw = [], 0
                continue
            # 行末禁则：把行尾的「挪到下一行
            if cur[-1] in NO_END and len(cur) > 1:
                last = cur.pop()
                out.append(''.join(cur))
                cur, curw = [last, ch], w(last) + cw
                continue
            out.append(''.join(cur)); cur, curw = [ch], cw
        else:
            cur.append(ch); curw += cw
    if cur:
        out.append(''.join(cur))
    return out


def rows(text, W):
    res = []
    for hard in text.split('\n'):
        if hard == '':
            continue
        res.extend(wrap_line(hard, W))
    return res


def total(text, W):
    return sum(len(wrap_line(h, W)) for h in text.split('\n') if h)
