# -*- coding: utf-8 -*-
# 看 script/51 里 JP run 之间的分隔字节，判断分页结构
import sys
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
import cpk
c = cpk.CPK(os.path.join(VNTRANS_HOME, '_work_nisefd/INSTALL.cpk'))
c.by_name = {e['name']: e for e in c.entries if e.get('name')}
raw = c.raw(c.by_name['script/51'])
n = len(raw)

# 定位所有 JP run 的起止
sep = lambda b: b in (0xff, 0x80, 0x00)
runs = []  # (start, end)
i = 0
while i < n:
    if sep(raw[i]):
        i += 1; continue
    j = i
    while j < n and not sep(raw[j]):
        j += 1
    seg = raw[i:j].decode('cp932','ignore')
    if any('぀'<=ch<='ヿ' or '一'<=ch<='龠' for ch in seg):
        runs.append((i, j))
    i = j

print('JP runs:', len(runs))
# 打印前 12 个 run 的起止 + 前面分隔字节(最多前 16 字节)
for k,(s,e) in enumerate(runs[:12]):
    pre = raw[max(0,s-16):s]
    # 把 00/ff/80 显示为 . 方便看
    pre_s = ' '.join(('%02x'%b if b not in (0,0xff,0x80) else ('.' if b==0 else ('F' if b==0xff else '8'))) for b in pre)
    print(f'[{k:2d}] {s:5d}-{e:5d} pre=[{pre_s}]  text={raw[s:e].decode("cp932","ignore")[:30]!r}')
