# -*- coding: utf-8 -*-
# 验证修正后的 extract_synopsis 解析
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

def is_header(j):
    return j+6 < n and raw[j+3] not in (0xff,0x00) and raw[j+4]==0x00 and raw[j+6]==0x00

records = []
i = 0
while True:
    j = raw.find(marker, i)
    if j < 0: break
    if is_header(j):
        PP = raw[j+3]; NN = raw[j+5]
        q = j+7
        while q < n and raw[q] != 0: q += 1
        text = raw[j+7:q].decode('cp932','ignore')
        records.append((PP, NN, text))
        i = q
    else:
        i = j + 1

# first block 之前 (run[0])
jj = 0
while jj < n and not is_header(jj):
    jj = raw.find(marker, jj)
    if jj < 0: break
    if not is_header(jj):
        # 找下一个可能的起始(逐字节)
        nxt = raw.find(marker, jj+1)
        if nxt < 0: jj = -1; break
        jj = nxt
first_header = jj if (jj is not None and jj>=0) else n
pre = raw[:first_header].replace(b'\xff',b'\x00').replace(b'\x80',b'\x00').decode('cp932','ignore')
fr = [s for s in pre.split('\x00') if re.search(r'[぀-ヿ一-龠]', s)]

pages = defaultdict(list)
if fr:
    pages[1].insert(0, (-1, ''.join(fr)))
for PP, NN, text in records:
    pages[PP].append((NN, text))

out = []
for PP in sorted(pages):
    lines = sorted(pages[PP], key=lambda x: x[0])
    out.append(''.join(t for _,t in lines))

total = sum(len(x) for x in out)
print('records:', len(records), 'pages:', len(out), 'total chars:', total)
print('=== page1 ==='); print(out[0])
print('=== page2 ==='); print(out[1])
print('=== page3 ==='); print(out[2])
print('=== page 18 (应含 小島家...) ===')
if len(out) > 17: print(out[17][:120])
