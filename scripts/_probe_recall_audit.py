# -*- coding: utf-8 -*-
"""Recall 审计探针：① 选项载体形态 ② 零文本 .ks 性质核验。"""
import os, re, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xp3 import XP3
from recall_extract import read_ks

XP3_PATH = os.path.join(VNTRANS_HOME, "_work_recall/src/[JP]Recall/data.xp3")
xp3 = XP3(XP3_PATH)
ks = sorted(n for n in xp3.files if n.lower().endswith('.ks'))

# ---- ① 选项载体形态：统计各选项标签出现次数 + 抽 3 例上下文 ----
opt_pat = re.compile(r'\[(?:link|endlink|select|button|lbutton|ch|choice|jump)\b', re.I)
counts = {}
examples = []
for name in ks:
    t = read_ks(xp3, name)
    for m in opt_pat.finditer(t):
        tag = m.group(0).lower()
        counts[tag] = counts.get(tag, 0) + 1
    # 抽取含 link/select 的前几个有内容的示例
    if len(examples) < 4:
        for mm in re.finditer(r'.{0,80}\[link.{0,120}', t, re.I | re.S):
            examples.append((name, mm.group(0).replace('\n','\\n')))
            break
print("=== 选项标签计数（全 .ks）===")
for k, v in sorted(counts.items(), key=lambda x:-x[1]):
    print(f"  {k:12} {v}")
print("\n=== [link 上下文示例 ===")
for nm, ex in examples:
    print(f"[{nm}]\n  {ex}\n")

# ---- ② 零文本 .ks 性质核验 ----
print("=== 零文本 .ks 清单 + 性质标记 ===")
zero = []
for name in ks:
    t = read_ks(xp3, name)
    if not t.strip():
        zero.append((name, 'EMPTY_RAW'))
        continue
    # 复用 parse 仅统计 box（轻量）：这里直接按页界粗数
    nb = t.count('[p]') + t.count('[e]') + t.count('[er]') + t.count('[ct]') + t.count('[cm]')
    nscript = t.count('[iscript') + t.count('@iscript') + t.count('[endscript')
    ndef = len(re.findall(r'\*[\w\-]+', t))  # 标签/标号
    ninvoke = len(re.findall(r'@(?:call|eval|jump|macro|if|while|for)\b', t, re.I))
    # 是否有任何“可见文本”倾向：含平假名片假名汉字
    nja = len(re.findall(r'[\u3040-\u30ff\u4e00-\u9fff]', t))
    if nb == 0 and nja < 50 and (nscript > 0 or ndef > 0 or ninvoke > 0):
        zero.append((name, f'sys(box=0,ja={nja},script={nscript},def={ndef},invoke={ninvoke})'))
print(f"  零/系统类文件数: {len(zero)}")
for nm, tag in zero:
    print(f"  {tag:55} {nm}")
