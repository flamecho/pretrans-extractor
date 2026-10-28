#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""非日文字符台账审计：把每部成品里「kana/汉字/CJK标点/全角符号」以外的字符全部列出，
并给出「出现次数 + 首现行 + 该行上下文」，供人工逐字判定「它是什么」。

用法：
  python scripts/charset_audit.py                 # 全部 27 部，摘要（每种字符 1 条样例）
  python scripts/charset_audit.py <成品.txt>      # 单部，全量
  python scripts/charset_audit.py --sus           # 只列「可疑类」（ASCII 标点/控制形）
"""
import os
import sys
import io
import argparse

T = '提取结果'
SUS = set('%&$#@*\\|<>{}[]_=+^~`"\';:,.!?/')


def cjk(ch):
    o = ord(ch)
    return (0x3040 <= o <= 0x30ff) or (0x3400 <= o <= 0x4dbf) or (0x4e00 <= o <= 0x9fff) \
        or (0x3000 <= o <= 0x303f) or (0xff01 <= o <= 0xff60) or (0xffe0 <= o <= 0xffee)


def audit(path, sus_only=False, full=False):
    L = io.open(path, encoding='utf-8-sig').read().split('\n')
    inv = {}
    for i, l in enumerate(L):
        for ch in l:
            if ch == '\r' or cjk(ch):
                continue
            e = inv.setdefault(ch, [0, i + 1, l])
            e[0] += 1
    name = os.path.basename(path)[:-4]
    print('=== %s（%d 行，非日文字符 %d 种）' % (name, len([x for x in L if x.strip()]), len(inv)))
    items = sorted(inv.items(), key=lambda kv: -kv[1][0])
    for ch, (n, ln, ctx) in items:
        if sus_only and ch not in SUS:
            continue
        tag = ''
        if ch in SUS:
            tag = ' ←可疑'
        print('   %-4r U+%04X ×%-6d L%-6d| %s%s' % (ch, ord(ch), n, ln, ctx[:70], tag))
        if not full and n <= 1:
            pass
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='*')
    ap.add_argument('--sus', action='store_true')
    a = ap.parse_args()
    targets = a.files if a.files else [os.path.join(T, f) for f in sorted(os.listdir(T)) if f.endswith('.txt')]
    for p in targets:
        audit(p, a.sus)


if __name__ == '__main__':
    main()
