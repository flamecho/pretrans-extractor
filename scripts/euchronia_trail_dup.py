#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""定位成品的「相邻重复行」源于哪个脚本、何种结构（用于判是否互斥分支重复）。"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import euchronia_trail_extract as E

root = sys.argv[1]
src = {}
lines = []
for fn, txt in E.iter_scripts(root):
    if not re.match(r'^\d\d_', fn) or 'test' in fn or fn == '00_live2d_check':
        continue
    src[fn] = txt.replace('\r\n', '\n')

# 重跑一遍成行，但记录文件边界
prev = None
outfile = sys.argv[2]
cur = open(outfile, encoding='utf-8-sig').read().split('\n')[:-1]
# 直接扫描源里的「同名重复块」结构
for fn, txt in sorted(src.items()):
    blocks = []
    for chunk in re.split(r'\n\s*\n', txt):
        ls = [E.clean_line(x) for x in chunk.split('\n')]
        ls = [x for x in ls if x]
        if ls and E.PLATE.match(ls[0]):
            ls = ls[1:]
        b = ''.join(ls)
        if b:
            blocks.append(b)
    for i in range(1, len(blocks)):
        if blocks[i] == blocks[i - 1]:
            print('%s  #%d  %s' % (fn, i, blocks[i][:60]))
