#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""用 cd_solve 的「条目→相手役」映射跑一次成品（诊断用，不写 提取结果/）。

用法：python scripts/cd_apply.py <输出路径>
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cpk import CPK
import vridge_psp_run as R
import cd_solve as S
from vridge_cs_customdrive import (CPK as CPK_PATH, CHARSET, SPECIAL, NAME_SUB,
                                   TITLE_OPS, DROP_EXACT, CAST, PROTAG_GIVEN,
                                   FF0C_FALLBACK)

out_path = sys.argv[1]
ents = S.load()
out = S.solve(ents)
MAP = {}
for x, o in zip(ents, out):
    vals = {}
    for fi, f in enumerate(x['frames']):
        if f['ff']:
            vals[f['st']] = S.fill_of(x, o, fi)
    MAP[x['name']] = vals

c = CPK(CPK_PATH)
E = sorted([e for e in c.entries if e['name'] and e['name'].isdigit()],
           key=lambda e: int(e['name']))
lines, ph = [], 0
for e in E:
    d = c.raw(e)
    tk = R.toks(d)
    starts = R.plate_spans(tk, CHARSET, SPECIAL, PROTAG_GIVEN)[0]
    import bisect
    plan = {}
    for k, (op, _) in enumerate(tk):
        if op == 0xFF0C:
            b = bisect.bisect_left(starts, k) - 1
            key = starts[b] if 0 <= b < len(starts) else -1
            v = MAP.get(e['name'], {}).get(key)
            plan[k] = (PROTAG_GIVEN if v == S.PROTAG else CAST[v]) if v else FF0C_FALLBACK
            if not v:
                ph += 1
    # 复用 extract_entry：先把 plan_ff0c 换成固定 plan
    old = R.plan_ff0c
    R.plan_ff0c = lambda tk2, *a, **kw: plan
    try:
        boxes = R.extract_entry(d, CHARSET, SPECIAL, NAME_SUB, TITLE_OPS,
                                (CAST, PROTAG_GIVEN, FF0C_FALLBACK))
    finally:
        R.plan_ff0c = old
    for s in boxes:
        if R.UNDECODED in s:
            continue
        s = R.clean_line(s)
        if s in DROP_EXACT:
            continue
        if R.keep(s):
            lines.append(s)
res = []
for s in lines:
    if res and res[-1] == s:
        continue
    res.append(s)
with open(out_path, 'w', encoding='utf-8-sig', newline='\n') as f:
    f.write('\n'.join(res) + '\n')
print('entries %d lines %d 未解 token %d  〔相手役〕行 %d'
      % (len(E), len(res), ph, sum(1 for s in res if FF0C_FALLBACK in s)))
