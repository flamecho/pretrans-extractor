# -*- coding: utf-8 -*-
# 离线验证新 extract_synopsis: 结构化解析 + 按页归并
import sys, re
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

heads = []
i = 0
while True:
    j = raw.find(marker, i)
    if j < 0: break
    if j+3 < n and raw[j+3] != 0xff:
        heads.append(j)
    i = j + 3

pages = defaultdict(list)   # PP -> [(NN, text)]
first_block = None
if heads:
    # 第一个 head 之前的 JP 文本 = 第1页首行 (NN=00)
    pre = raw[:heads[0]].replace(b'\xff',b'\x00').replace(b'\x80',b'\x00').decode('cp932','ignore')
    fr = [s for s in pre.split('\x00') if re.search(r'[぀-ヿ一-龠]', s)]
    if fr:
        first_block = ''.join(fr)

for p in heads:
    PP = raw[p+3]; NN = raw[p+5]
    q = p+7
    while q < n and raw[q] != 0:
        q += 1
    text = raw[p+7:q].decode('cp932','ignore')
    pages[PP].append((NN, text))

# 归并: 第1页 = first_block + PP==1 的记录; 其余按 PP 排序, 页内按 NN 排序拼接
out = []
pp_keys = sorted(pages)
# 把 first_block 放进 PP=1 最前
if 1 in pages and first_block is not None:
    pages[1].insert(0, (-1, first_block))
for PP in pp_keys:
    lines = sorted(pages[PP], key=lambda x: x[0])
    out.append(''.join(t for _,t in lines))

total = sum(len(x) for x in out)
print('pages:', len(out), 'total chars:', total)
for k,x in enumerate(out[:4]):
    print(f'--- page {k+1} ({len(x)} chars) ---')
    print(x)
print('...')
print('--- last page ---')
print(out[-1])
