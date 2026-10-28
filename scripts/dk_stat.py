#!/usr/bin/env python3
"""dk_stat.py -- DATA01 全条目解码闭合统计（写报告用）。"""
import sys, struct, re, collections
sys.path.insert(0, 'tools')
from dk_lib import walk, expand

ok = bad = 0
badname = []
scpt = 0
jp = 0
fail_flags = collections.Counter()
for vol, nm, cs, us, fl, seg in walk(['DATA01']):
    try:
        o = expand(seg, us, fl)
        ok += 1
    except Exception as e:
        bad += 1
        fail_flags[fl] += 1
        if len(badname) < 3:
            badname.append((nm, str(e)[:40]))
        continue
    if len(o) != us:
        badname.append(('SIZE ' + nm, '%d!=%d' % (len(o), us)))
    if o[:4] == b'SCPT':
        scpt += 1
print('DATA01 条目 %d：解码成功 %d / 失败 %d（flags %s）' % (ok + bad, ok, bad, dict(fail_flags)))
print('SCPT 脚本', scpt, '失败样本', badname[:3])
