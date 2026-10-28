#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""：导出 bundle 内指定 TextAsset 原文到文件。"""
import sys, os
import UnityPy

src, outdir = sys.argv[1], sys.argv[2]
want = set(sys.argv[3:])
env = UnityPy.load(src)
os.makedirs(outdir, exist_ok=True)
n = 0
for o in env.objects:
    if o.type.name != 'TextAsset':
        continue
    d = o.read()
    name = d.m_Name
    if want and name not in want:
        continue
    raw = d.m_Script if isinstance(d.m_Script, bytes) else str(d.m_Script).encode('utf-8', 'replace')
    p = os.path.join(outdir, name + '.txt')
    open(p, 'wb').write(raw)
    n += 1
print('dumped', n, '->', outdir)
