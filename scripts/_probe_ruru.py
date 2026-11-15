# -*- coding: utf-8 -*-
# 探查 ルル＃＃＃＃＃ 宏的原始字节与上下文
import sys
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
import cpk, nisenochigiri_fd_extract as F
from nisenochigiri_fd_extract import N

c = cpk.CPK(os.path.join(VNTRANS_HOME, '_work_nisefd/INSTALL.cpk'))
c.by_name = {e['name']: e for e in c.entries if e.get('name')}

needle = 'ルル'.encode('cp932')
hits = []
for e in c.entries:
    name = e.get('name', '')
    if not name.startswith('script/'):
        continue
    raw = c.raw(e)
    if raw[:5] != b'STCM2':
        continue
    idx = 0
    while True:
        j = raw.find(needle, idx)
        if j < 0:
            break
        # 截取包含宏的上下文
        seg = raw[max(0, j-40): j+60]
        # 找可读文本
        txt = seg.decode('cp932', 'ignore')
        hits.append((name, j, repr(txt)))
        idx = j + len(needle)

print('total ルル hits:', len(hits))
for name, j, t in hits[:40]:
    print(name, j, t)
