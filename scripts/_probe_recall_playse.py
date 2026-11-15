# -*- coding: utf-8 -*-
"""精确打印含 空間歪み 的原始行（repr），定位 playse 标签泄漏成因。"""
import os, re, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xp3 import XP3
from recall_extract import read_ks

XP3_PATH = os.path.join(VNTRANS_HOME, "_work_recall/src/[JP]Recall/data.xp3")
xp3 = XP3(XP3_PATH)
ks = sorted(n for n in xp3.files if n.lower().endswith('.ks'))

for name in ks:
    t = read_ks(xp3, name)
    for line in t.split('\n'):
        if '空間歪み' in line and 'ああ' in line:
            print(f"[{name}] repr>>> {line!r}")
        # 也打印含 playse 且括号不平衡的行
    # 统计：playse 出现但本行 '[' 数 != ']' 数
print("\n=== 括号不平衡的 playse 行（全作）===")
cnt=0
for name in ks:
    t = read_ks(xp3, name)
    for line in t.split('\n'):
        if 'playse' in line and line.count('[') != line.count(']'):
            print(f"[{name}] {line!r}")
            cnt+=1
            if cnt>=10: break
    if cnt>=10: break
