# -*- coding: utf-8 -*-
# 探查 ＃ (全角) 宏的全作形态 + #Name 宏系统
import sys, re
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
import cpk
c = cpk.CPK(os.path.join(VNTRANS_HOME, '_work_nisefd/INSTALL.cpk'))
c.by_name = {e['name']: e for e in c.entries if e.get('name')}

FH = '＃'.encode('utf-8')  # 全角 ＃ U+FF03
AH = b'#'                  # ASCII #

# 1) 全角 ＃ 出现的所有"名字串"形态
name_patterns = {}
total_fh = 0
# 2) #Name[1]/#Name[2] 出现位置
namevar = {}
for e in c.entries:
    name = e.get('name', '')
    if not name.startswith('script/'):
        continue
    raw = c.raw(e)
    total_fh += raw.count(FH)
    # 提取所有含 ＃ 的连续可见片段
    for m in re.finditer(FH + b'+', raw):
        # 取前后若干字符作为上下文
        s = max(0, m.start()-24); en = min(len(raw), m.end()+4)
        frag = raw[s:en].decode('cp932','ignore')
        # 只保留含日文/名字特征的
        if re.search(r'[぀-ヿ一-鿿]', frag):
            key = frag.strip()[:40]
            name_patterns[key] = name_patterns.get(key, 0) + 1
    for m in re.finditer(rb'#Name\[\d\]', raw):
        key = m.group().decode('ascii')
        namevar[key] = namevar.get(key, 0) + 1

print('=== 全角 ＃ 总出现次数:', total_fh)
print('=== 含 ＃ 的片段形态(按出现频次) top 25 ===')
for k, v in sorted(name_patterns.items(), key=lambda x:-x[1])[:25]:
    print(v, repr(k))
print()
print('=== #Name[n] 变量出现次数 ===')
for k, v in sorted(namevar.items(), key=lambda x:-x[1]):
    print(v, repr(k))
