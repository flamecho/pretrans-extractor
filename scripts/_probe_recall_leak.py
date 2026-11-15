# -*- coding: utf-8 -*-
"""定位 [playse... leakage 源 + 相邻重复行来源。"""
import os, re, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xp3 import XP3
from recall_extract import read_ks

XP3_PATH = os.path.join(VNTRANS_HOME, "_work_recall/src/[JP]Recall/data.xp3")
xp3 = XP3(XP3_PATH)
ks = sorted(n for n in xp3.files if n.lower().endswith('.ks'))

print("=== 含 '空間歪み' 的 .ks 上下文 ===")
for name in ks:
    t = read_ks(xp3, name)
    for m in re.finditer(r'.{0,50}空間歪み.{0,80}', t, re.S):
        print(f"[{name}] >>>{m.group(0).replace(chr(10),'\\\\n')}<<<")
        break

# 输出中相邻重复行来源
print("\n=== 输出 L150-170 ===")
data = open(os.path.join(VNTRANS_HOME, "提取结果/[JP]Recall.txt"), encoding='utf-8').read().split('\n')
for i in range(149, min(170, len(data))):
    print(f"  L{i+1}: {data[i]}")

# 统计相邻重复里，是否是同一 box 的 段行重复（两行完全相等且都短）
dups = [(i, data[i]) for i in range(len(data)-1) if data[i] and data[i] == data[i+1]]
print(f"\n=== 相邻重复 ×{len(dups)}；前 15 例 ===")
for i, l in dups[:15]:
    print(f"  L{i+1}: {l[:50]}")
# 重复行里的字符分布：是否大量来自战斗池
print("  重复行含 '・・・' 比例:", sum(1 for _,l in dups if '・・・' in l), "/", len(dups))
