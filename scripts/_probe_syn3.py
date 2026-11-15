# -*- coding: utf-8 -*-
# 解析 script/51 的 FF FF FF PP 00 NN 00 <text> 记录结构
import sys
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
import cpk
c = cpk.CPK(os.path.join(VNTRANS_HOME, '_work_nisefd/INSTALL.cpk'))
c.by_name = {e['name']: e for e in c.entries if e.get('name')}
raw = c.raw(c.by_name['script/51'])
n = len(raw)

# 找所有 FF FF FF 位置
marker = b'\xff\xff\xff'
positions = []
i = 0
while True:
    j = raw.find(marker, i)
    if j < 0: break
    positions.append(j); i = j + 3

print('FF FF FF markers:', len(positions))
# 每条记录: marker@p -> p+3=PP, p+4=00?, p+5=NN, p+6=00?, p+7..=text until 00
recs = []
for p in positions:
    PP = raw[p+3]
    b4 = raw[p+4]
    NN = raw[p+5]
    b6 = raw[p+6]
    # 文本从 p+7 起, 到下一个 00
    q = p+7
    while q < n and raw[q] != 0:
        q += 1
    text = raw[p+7:q].decode('cp932','ignore')
    recs.append((PP, NN, b4, b6, text))

# 统计页码 -> 行号集合
from collections import defaultdict
pages = defaultdict(list)
for PP, NN, b4, b6, text in recs:
    pages[PP].append((NN, text))

print('pages:', len(pages))
for PP in sorted(pages):
    lines = pages[PP]
    print(f'  PP={PP:2d} 行数={len(lines):2d}  首行={lines[0][1][:24]!r}  末行={lines[-1][1][:24]!r}')
print()
print('=== 样本: PP=01 全部 ===')
for NN, text in pages[1]:
    print(f'  NN={NN:2d} {text}')
