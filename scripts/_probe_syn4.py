# -*- coding: utf-8 -*-
# 稳健解析 script/51: 真实记录头 = FF FF FF 且 p+3 != 0xFF
import sys
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
import cpk
from collections import defaultdict
c = cpk.CPK(os.path.join(VNTRANS_HOME, '_work_nisefd/INSTALL.cpk'))
c.by_name = {e['name']: e for e in c.entries if e.get('name')}
raw = c.raw(c.by_name['script/51'])
n = len(raw)

marker = b'\xff\xff\xff'
# 收集真实记录头位置
heads = []
i = 0
while True:
    j = raw.find(marker, i)
    if j < 0: break
    if j + 3 < n and raw[j+3] != 0xff:   # 后跟非 FF = 真记录头
        heads.append(j)
    i = j + 3

print('real record heads:', len(heads))
pages = defaultdict(list)
for p in heads:
    PP = raw[p+3]
    if raw[p+4] != 0x00 or raw[p+6] != 0x00:
        continue
    NN = raw[p+5]
    q = p+7
    while q < n and raw[q] != 0:
        q += 1
    text = raw[p+7:q].decode('cp932','ignore')
    pages[PP].append((NN, text))

# 也抓第一个记录(文件头之后, 第一个 marker 之前的文本)
# 第一个 head 之前的 JP 文本
first_head = heads[0] if heads else n
# 从文件头找到第一个 JP 段: 简单用 split
seg0 = raw[:first_head].replace(b'\xff',b'\x00').replace(b'\x80',b'\x00').decode('cp932','ignore')
runs0 = [s for s in seg0.split('\x00') if any('぀'<=ch<='ヿ' or '一'<=ch<='龠' for ch in s)]
print('first-block JP runs before first head:', runs0)

total_chars = sum(len(t) for _,t in pages[PP] for PP in sorted(pages))
# 加首块
total_chars += sum(len(r) for r in runs0)
print('pages:', len(pages), 'total chars:', total_chars)
for PP in sorted(pages)[:3]:
    print(f'  PP={PP:2d} lines={len(pages[PP])} -> {pages[PP][0][1][:30]!r} ... {pages[PP][-1][1][:20]!r}')
