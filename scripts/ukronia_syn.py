#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""：剧本语法普查（命令词频、选项、占位符、块长分布）。"""
import os, re, sys, collections

root = sys.argv[1]
cmds = collections.Counter()
opt = collections.Counter()
odd = collections.Counter()
blocks = []
for fn in sorted(os.listdir(root)):
    if not fn.endswith('.txt'):
        continue
    txt = open(os.path.join(root, fn), encoding='utf-8-sig').read()
    for line in txt.split('\n'):
        s = line.strip()
        if not s or s.startswith(';//'):
            continue
        m = re.match(r'\[([^\]\s]+)', s)
        if m:
            cmds[m.group(1)] += 1
            if m.group(1) in ('seladd', 'sel', 'select', 'choice'):
                opt[s[:120]] += 1
        else:
            for ch in ('％', '%+&', '＆', '〔', '\\n', '[br]', '<', '＞'):
                if ch in s:
                    odd[ch] += 1
    cur = []
    for line in txt.split('\n'):
        s = line.rstrip()
        if s.strip() == '' or s.strip().startswith(';//'):
            if cur:
                blocks.append(cur)
                cur = []
            continue
        if s.strip().startswith('['):
            if cur:
                blocks.append(cur)
                cur = []
            continue
        cur.append(s)
    if cur:
        blocks.append(cur)

print('blocks', len(blocks))
ln = sorted(sum(len(x) for x in b) for b in blocks)
print('block len: min', ln[0], 'p50', ln[len(ln) // 2], 'p90', ln[int(len(ln) * 0.9)], 'p99', ln[int(len(ln) * 0.99)], 'max', ln[-1])
print('blocks>160:', sum(1 for v in ln if v > 160), '>300:', sum(1 for v in ln if v > 300))
print('lines per block:', collections.Counter(len(b) for b in blocks).most_common(8))
print('== top cmds ==')
for k, v in cmds.most_common(40):
    print('%8d %s' % (v, k))
print('== seladd samples ==')
for k, v in list(opt.items())[:5]:
    print(v, k)
print('== odd chars ==', odd)
