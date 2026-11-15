# -*- coding: utf-8 -*-
"""确认 [name] 用法（属性 vs 内容）及选项/link/ch 形态。"""
import os, re, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xp3 import XP3
from recall_extract import read_ks

XP3_PATH = os.path.join(VNTRANS_HOME, "_work_recall/src/[JP]Recall/data.xp3")
xp3 = XP3(XP3_PATH)
ks = sorted(n for n in xp3.files if n.lower().endswith('.ks'))

# [name 形态
attr = 0; content = 0; samples = []
for name in ks:
    t = read_ks(xp3, name)
    for m in re.finditer(r'\[name\b([^\]]*)\]', t):
        arg = m.group(1)
        if re.search(r'\bt\s*=', arg) or re.search(r'\bc\s*=', arg) or 'storage' in arg or 'page' in arg:
            attr += 1
        else:
            # 可能 [name]...[/name] 内容形式
            content += 1
            if len(samples) < 5:
                after = t[m.end():m.end()+40].split('[/name]')[0]
                samples.append((name, m.group(0), after))
print("=== [name] 用法 ===")
print(f"  属性式(t=/c=/storage=): {attr}   内容式([name]..[/name]): {content}")
for nm, tag, after in samples:
    print(f"  [{nm}] {tag}  -> after='{after}'")

# [choice 形态
print("\n=== [choice 全例（仅 3）===")
for name in ks:
    t = read_ks(xp3, name)
    for m in re.finditer(r'\[choice\b[^\]]*\]', t):
        print(f"  [{name}] {m.group(0)}")

# [link 是否都带 storage/target（导航）还是纯文本选择
print("\n=== [link 形态（前 5 例无 storage 的）===")
nav=0; other=0; oex=[]
for name in ks:
    t = read_ks(xp3, name)
    for m in re.finditer(r'\[link\b[^\]]*\]', t):
        tag=m.group(0)
        if 'storage' in tag or 'target' in tag: nav+=1
        else:
            other+=1
            if len(oex)<5: oex.append((name,tag))
print(f"  带 storage/target(导航): {nav}   其他: {other}")
for nm,tag in oex: print(f"  [{nm}] {tag}")
