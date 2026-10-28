#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""：剧本文件分类表（每文件正文行数 + 首行样本）。"""
import os, sys, re

root = sys.argv[1]
for fn in sorted(os.listdir(root)):
    if not fn.endswith('.txt'):
        continue
    txt = open(os.path.join(root, fn), encoding='utf-8-sig').read()
    n = 0
    first = ''
    for line in txt.split('\n'):
        s = line.strip()
        if not s or s.startswith(';//') or s.startswith('['):
            continue
        n += 1
        if not first:
            first = s[:40]
    print('%-24s %6d %s' % (fn[:-4], n, first))
