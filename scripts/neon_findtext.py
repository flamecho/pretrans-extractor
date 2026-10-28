#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 UnityPy 逐个加载 bundle（真解压），统计对象 raw 里的假名数量，找出「文本库」所在 bundle。
用法: NCA_KEY=<key> python scripts/neon_findtext.py <nca> <min_size> <max_size> [limit]
"""
import sys, os, re, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from neon_nca import Sec, BucketRomfs, parse_romfs
import UnityPy

nca = sys.argv[1]
lo = int(sys.argv[2]); hi = int(sys.argv[3])
limit = int(sys.argv[4]) if len(sys.argv) > 4 else 10 ** 9

sec = Sec(nca)
b = BucketRomfs(sec, 1)
b.sid = 1
files, fd = parse_romfs(b)
KANA = re.compile(rb'(?:[\xe3][\x81\x82][\x80-\xbf]){3,}')
tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '_w_W2_neon', 'tmp_scan.bundle')
rows = []
n = 0
for name, o, s in files:
    if not name.endswith('.bundle') or not (lo <= s <= hi):
        continue
    n += 1
    if n > limit:
        break
    try:
        d = b.read(o, s)
        with open(tmp, 'wb') as f:
            f.write(d)
        env = UnityPy.load(tmp)
    except Exception:
        continue
    best = 0
    for obj in env.objects:
        try:
            raw = obj.get_raw_data()
        except Exception:
            continue
        k = len(KANA.findall(raw[:4 << 20]))
        if k > best:
            best = k
    if best > 100:
        rows.append((best, s, name))
        print('HIT kana=%d size=%d %s' % (best, s, name), flush=True)
rows.sort(reverse=True)
print('scanned', n, 'hits', len(rows))
