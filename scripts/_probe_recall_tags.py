# -*- coding: utf-8 -*-
"""全 .ks 标签频率统计（去重到顶层 tag 名），确认页面/段界/选项/宏。"""
import os, re, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xp3 import XP3
from recall_extract import read_ks

XP3_PATH = os.path.join(VNTRANS_HOME, "_work_recall/src/[JP]Recall/data.xp3")
xp3 = XP3(XP3_PATH)
ks = sorted(n for n in xp3.files if n.lower().endswith('.ks'))

cnt = Counter()
for name in ks:
    t = read_ks(xp3, name)
    for m in re.finditer(r'\[([a-zA-Z_\u0080-\u9fff][^\]\[\s=]{0,30})', t):
        cnt[m.group(1).lower()] += 1

print("=== 顶层标签 Top 60（全 .ks）===")
for tag, n in cnt.most_common(60):
    print(f"  {tag:18} {n}")
print("\n总不同标签数:", len(cnt))

# 正常对话文件 break 分布（验证 [r] 为 intra-page, [p]/[e] 为 page）
print("\n=== 正常对话文件 break 分布 ===")
normal = ['scenario3/EDカオス.ks','scenario/プロローグ.ks','scenario/戦術指示.ks','scenario/難易度設定.ks']
for nm in normal:
    t = read_ks(xp3, nm) if nm in ks else ''
    if not t:
        # 找相似名
        cand = [k for k in ks if nm.split('/')[-1][:4] in k]
        print(f"  {nm}: not found; candidates={cand[:3]}")
        continue
    b = {x: t.count('['+x+']') for x in ['p','e','er','ct','cm','pe','ple','r','l','waitclick']}
    print(f"  {nm}: {b}")
