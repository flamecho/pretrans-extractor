#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SympathyKiss STCM2L 单段 opcode 追踪（看「同句两版 / 掩码 ＃＃＃ / 断行」在代码层长什么样）。

用法: python scripts/symp_trace.py <SCRIPT目录> <关键词>
"""
import sys, os, glob, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sympathy_extract import walk, BODY, VARIANT, TITLE, CHOICE, FLUSH, is_text, clean

NAME = {}
for k in ('0x54E4C', '0x54568', '0x544A0'):
    NAME[int(k, 16)] = 'NAME?'


def opname(op):
    if op in BODY:
        return 'BODY'
    if op in VARIANT:
        return 'VARIANT'
    if op in TITLE:
        return 'TITLE'
    if op in CHOICE:
        return 'CHOICE'
    if op in FLUSH:
        return 'FLUSH(收框)'
    return 'op_0x%X' % op


def trace(scripts, key):
    for src in scripts:
        for fn in sorted(glob.glob(os.path.join(src, '*.DAT')),
                         key=lambda p: int(''.join(c for c in os.path.basename(p) if c.isdigit()) or 0)):
            d = open(fn, 'rb').read()
            if not d.startswith(b'STCM2L'):
                continue
            ops = walk(d)
            hit = [i for i, (op, ss) in enumerate(ops)
                   if op in BODY and ss and ss[0] and key in ss[0]]
            if not hit:
                continue
            print('=== %s  命中 op#%s / 共 %d 条指令' % (os.path.basename(fn), hit, len(ops)))
            for h in hit:
                lo, hi = max(0, h - 6), min(len(ops), h + 8)
                for i in range(lo, hi):
                    op, ss = ops[i]
                    print('  %s #%-5d %-12s argc=%d  %s'
                          % ('→' if i == h else ' ', i, opname(op), len(ss),
                             ' ｜ '.join(repr(s)[:70] if s else '∅' for s in ss[:4])))
                print('  ---')


if __name__ == '__main__':
    trace(sys.argv[1].split(','), sys.argv[2])
