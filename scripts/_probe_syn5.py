# -*- coding: utf-8 -*-
# dump 每个真实记录头后 14 字节, 钉死头部格式
import sys
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
import cpk
c = cpk.CPK(os.path.join(VNTRANS_HOME, '_work_nisefd/INSTALL.cpk'))
c.by_name = {e['name']: e for e in c.entries if e.get('name')}
raw = c.raw(c.by_name['script/51'])
n = len(raw)
marker = b'\xff\xff\xff'
heads = []
i = 0
while True:
    j = raw.find(marker, i)
    if j < 0: break
    if j+3 < n and raw[j+3] != 0xff:
        heads.append(j)
    i = j + 3
print('real heads:', len(heads))
for k,p in enumerate(heads[:14]):
    after = raw[p:p+14]
    bs = ' '.join('%02x'%b for b in after)
    print(f'head[{k:2d}] @{p:5d}: {bs}')
