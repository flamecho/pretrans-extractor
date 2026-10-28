#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""：闭合校验（[next storage] 目标是否都在、排除清单、块/页/选项计数）。"""
import os, re, sys
import UnityPy

BUNDLE = sys.argv[1]
env = UnityPy.load(BUNDLE)
names, texts = [], {}
for o in env.objects:
    if o.type.name != 'TextAsset':
        continue
    d = o.read()
    raw = d.m_Script if isinstance(d.m_Script, bytes) else str(d.m_Script).encode('utf-8', 'replace')
    names.append(d.m_Name)
    texts[d.m_Name] = raw.decode('utf-8-sig', 'replace')

used = sorted(n for n in names if re.match(r'^\d\d_', n) and 'test' not in n)
skipped = sorted(set(names) - set(used))
print('TextAsset 总数', len(names), '入库', len(used), '排除', len(skipped))
print('排除清单:', skipped)

refs = set()
for n in used:
    for m in re.finditer(r'\[next\s+storage="([^"]+)"', texts[n]):
        refs.add(m.group(1).replace('.txt', ''))
missing = sorted(r for r in refs if r not in texts)
print('next storage 引用', len(refs), '缺失', len(missing), missing[:10])

# 每文件链首/链尾（无入边者 = 入口）
inb = {}
for n in used:
    for m in re.finditer(r'\[next\s+storage="([^"]+)"', texts[n]):
        inb.setdefault(m.group(1).replace('.txt', ''), []).append(n)
entries = [n for n in used if n not in inb]
print('无入边文件（入口候选）', len(entries), entries[:12])
