#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""：novel mode（textmode=3）分段统计。"""
import os, sys, re, collections

root = sys.argv[1]
pages = []
in_novel = False
cur = []
blocks = []
for fn in sorted(os.listdir(root)):
    if not fn.endswith('.txt'):
        continue
    txt = open(os.path.join(root, fn), encoding='utf-8-sig').read()
    for line in txt.split('\n'):
        s = line.strip()
        m = re.match(r'\[textmode=(\d)\]', s)
        if m:
            if cur:
                pages.append(cur); cur = []
            in_novel = (m.group(1) == '3')
            continue
        if s == '[nextpage]':
            if cur:
                pages.append(cur); cur = []
            continue
        if not s or s.startswith(';//') or s.startswith('['):
            if s.startswith('[') and cur and in_novel:
                # 命令打断：仍留在同一页
                pass
            continue
        if in_novel:
            cur.append(s)
if cur:
    pages.append(cur)

lens = sorted(sum(len(x) for x in p) for p in pages)
print('novel pages', len(pages))
if lens:
    print('len p10 %d p50 %d p90 %d max %d' % (lens[len(lens)//10], lens[len(lens)//2], lens[int(len(lens)*.9)], lens[-1]))
    print('paras per page', collections.Counter(len(p) for p in pages).most_common(10))
    print('sample:', pages[0][:3] if pages else None)
