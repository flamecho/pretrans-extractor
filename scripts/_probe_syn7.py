# -*- coding: utf-8 -*-
# 核对: 简单split的所有JP段 中, 哪些不被结构化记录覆盖 -> 是否真垃圾
import sys, re
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
import cpk
c = cpk.CPK(os.path.join(VNTRANS_HOME, '_work_nisefd/INSTALL.cpk'))
c.by_name = {e['name']: e for e in c.entries if e.get('name')}
raw = c.raw(c.by_name['script/51'])
n = len(raw)
marker = b'\xff\xff\xff'

# 结构化记录覆盖的文本字节区间
heads = []
i = 0
while True:
    j = raw.find(marker, i)
    if j < 0: break
    if j+3 < n and raw[j+3] != 0xff:
        heads.append(j)
    i = j + 3
covered = set()
for p in heads:
    q = p+7
    while q < n and raw[q] != 0: q += 1
    for off in range(p+7, q):
        covered.add(off)
# first block
if heads:
    pre = raw[:heads[0]]
    # 第一个 JP 段字节区间 (简单)
    seg = pre.replace(b'\xff',b'\x00').replace(b'\x80',b'\x00').decode('cp932','ignore')
    runs0 = [(s) for s in seg.split('\x00') if re.search(r'[぀-ヿ一-龠]', s)]
    # 粗略: 第一个 JP 串起点
    m = re.search(r'[぀-ヿ一-龠]', seg)
    if m:
        # 找 raw 中该串位置
        bs = runs0[0].encode('cp932')
        k = pre.find(bs)
        if k>=0:
            for off in range(k, k+len(bs)): covered.add(off)

# 简单split所有JP段, 检查是否被覆盖(其首字节是否在covered)
sep = lambda b: b in (0xff,0x80,0x00)
runs = []
i=0
while i<n:
    if sep(raw[i]): i+=1; continue
    j=i
    while j<n and not sep(raw[j]): j+=1
    seg=raw[i:j].decode('cp932','ignore')
    if re.search(r'[぀-ヿ一-龠]', seg):
        runs.append((i,j,seg))
    i=j

uncovered=[]
for s,e,seg in runs:
    if not (s in covered):
        uncovered.append(seg)
print('simple JP runs:', len(runs))
print('uncovered (not in structural records):', len(uncovered))
for s in uncovered:
    print('  ', repr(s[:60]), 'len', len(s))
