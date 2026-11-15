# -*- coding: utf-8 -*-
"""为排除列表建证据：每个零-box/plugin 文件的显示标签计数 + TJS 代码块标记。"""
import os, re, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xp3 import XP3
from recall_extract import read_ks

XP3_PATH = os.path.join(VNTRANS_HOME, "_work_recall/src/[JP]Recall/data.xp3")
xp3 = XP3(XP3_PATH)
ks = sorted(n for n in xp3.files if n.lower().endswith('.ks'))

DISP = ['e','p','er','ct','cm','pe','ple','clear','r','waitclick','link','l','select','button']
print(f"{'FILE':52} {'plg':3} " + ' '.join(f"{t:>3}" for t in DISP) + "  brace_blk")
for name in ks:
    t = read_ks(xp3, name)
    if not t.strip():
        continue
    tags = {x: t.count('['+x+']') for x in DISP}
    brace = sum(1 for ln in t.split('\n') if ln.strip().startswith('{'))
    total_disp = sum(tags.values())
    is_plg = name.lower().startswith('plugin/')
    # 仅关注“无显示标签 / plugin / 疑似代码”的文件
    if total_disp == 0 or is_plg or brace > 5:
        print(f"{name:52} {str(is_plg):3} " + ' '.join(f"{tags[x]:>3}" for x in DISP) + f"  {brace}")
