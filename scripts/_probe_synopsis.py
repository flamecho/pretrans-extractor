# -*- coding: utf-8 -*-
# 探查 script/51 あらすじ 的原始字节分块结构
import sys
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
import cpk
c = cpk.CPK(os.path.join(VNTRANS_HOME, '_work_nisefd/INSTALL.cpk'))
c.by_name = {e['name']: e for e in c.entries if e.get('name')}
raw = c.raw(c.by_name['script/51'])
print('total len:', len(raw), 'first8:', raw[:8].hex())

# 找所有 0xff / 0x80 分隔符位置，统计连续日文段
# 把 0xff/0x80/0x00 都当分隔
sep = lambda b: b in (0xff, 0x80, 0x00)
# 遍历，记录"日文 run"的起止与长度
runs = []
i = 0
n = len(raw)
while i < n:
    b = raw[i]
    if sep(b):
        i += 1
        continue
    j = i
    buf = bytearray()
    while j < n and not sep(raw[j]):
        buf.append(raw[j]); j += 1
    seg = bytes(buf).decode('cp932', 'ignore')
    if any('぀' <= ch <= 'ヿ' or '一' <= ch <= '龠' for ch in seg):
        runs.append(seg)
    i = j

print('JP runs count:', len(runs))
tot = 0
for k, s in enumerate(runs):
    tot += len(s)
    print(f'  [{k:2d}] len={len(s):4d}  {s[:50]!r}')
print('total JP chars:', tot)
