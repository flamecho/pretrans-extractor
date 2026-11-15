# -*- coding: utf-8 -*-
import sys
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, "tools"))
import nisenochigiri_extract as N
import cpk

CPK_PATH = os.path.join(VNTRANS_HOME, "_work_nisefd/INSTALL.cpk")
c = cpk.CPK(CPK_PATH)
c.by_name = {e['name']: e for e in c.entries if e.get('name')}
all_stcm = [e['name'] for e in c.entries
            if (e.get('name','') or '').startswith('script/') and c.raw(e)[:5] == b'STCM2']

NAME_OP = {0x7a, 0x1dd, 0x1d3}
from collections import Counter
kdist = Counter()          # (cmd, k) -> count
samples = {}              # (cmd,k) -> list of sample texts
mizu = []                 # 水輪 occurrences (cmd,k,text)
for fn in all_stcm:
    raw = c.raw(c.by_name[fn])
    for u in N.units(raw):
        for k, t, cmd, arg in N.recs(u):
            if cmd in NAME_OP:
                s = N.clean(t).strip()
                kdist[(cmd,k)] += 1
                if len(samples.get((cmd,k),[])) < 6:
                    samples.setdefault((cmd,k),[]).append(s)
                if '水輪' in s or 'みず' in s:
                    mizu.append((cmd,k,s,fn))
print("=== (cmd, k) distribution for NAME_OP ===")
for key in sorted(kdist):
    print(key, kdist[key], samples.get(key,[]))
print("=== 水輪 / みず hits ===")
for x in mizu[:40]:
    print(x)
print("total 水輪 hits:", len(mizu))
