# -*- coding: utf-8 -*-
import sys, re
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
import cpk
c = cpk.CPK(os.path.join(VNTRANS_HOME, '_work_nisefd/INSTALL.cpk'))
c.by_name = {e['name']: e for e in c.entries if e.get('name')}

FH = '＃'.encode('cp932')   # 0x81 0xDD

# 全角 ＃ 的连续串形态
runs = {}
total = 0
for e in c.entries:
    name = e.get('name', '')
    if not name.startswith('script/'):
        continue
    raw = c.raw(e)
    for m in re.finditer(re.escape(FH) + b'+', raw):
        total += 1
        s = max(0, m.start()-30); en = min(len(raw), m.end()+2)
        frag = raw[s:en].decode('cp932', 'ignore')
        # 只保留与名字相邻的
        if re.search(r'[぀-ヿ一-鿿]', frag):
            key = frag.strip()[:46]
            runs[key] = runs.get(key, 0) + 1

print('含日本语+＃ 的片段命中:', total)
print('=== 形态 top 30 ===')
for k, v in sorted(runs.items(), key=lambda x: -x[1])[:30]:
    print(v, repr(k))
