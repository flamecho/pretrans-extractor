#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""：列出 Unity bundle 里的 TextAsset（名称/大小/首行），判定正文载体。"""
import sys
import UnityPy

env = UnityPy.load(sys.argv[1])
rows = []
for o in env.objects:
    if o.type.name != 'TextAsset':
        continue
    d = o.read()
    raw = d.m_Script if isinstance(d.m_Script, bytes) else str(d.m_Script).encode('utf-8', 'replace')
    try:
        txt = raw.decode('utf-8')
    except UnicodeDecodeError:
        txt = raw.decode('utf-16-le', 'replace')
    rows.append((d.m_Name if hasattr(d, 'm_Name') else '?', len(raw), txt))
rows.sort(key=lambda r: -r[1])
for n, ln, t in rows:
    head = t[:70].replace('\n', '\\n')
    jp = sum(1 for ch in t[:4000] if '\u3040' <= ch <= '\u30ff' or '\u4e00' <= ch <= '\u9fff')
    print('%-40s %9d jp=%4d | %s' % (n, ln, jp, head))
