#!/usr/bin/env python3
# ASCII scan: classify lines with Latin letters into 正常原文 / 脚本残留 / 系统菜单.
import re
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
TXT = os.path.join(VNTRANS_HOME, "提取结果/[PC-JP]Psychic Rain.txt")
lines = open(TXT, encoding="utf-8").read().split("\n")
latin = [ln for ln in lines if re.search(r'[A-Za-z]', ln)]
print("=== lines containing A-Za-z: %d / %d ==="%(len(latin), len(lines)))
residue, normal, sysui = [], [], []
for ln in latin:
    low = ln.lower()
    if re.search(r'\.exe|\.dat|\.dll|0x[0-9a-f]{2,}|malie_|vm_code|funcname|parse_|_ms_message|struct', low):
        residue.append(ln)
    elif re.search(r'^(config|system|menu|save|load|title|yes|no|back|next|start|exit|window|name)[:：]', low):
        sysui.append(ln)
    else:
        normal.append(ln)
print("  [脚本残留] %d:"%len(residue))
for ln in residue[:20]: print("    >", ln[:90])
print("  [系统菜单] %d:"%len(sysui))
for ln in sysui[:20]: print("    >", ln[:90])
print("  [正常原文(德/英台词/外文)] %d (sample):"%len(normal))
for ln in normal[:15]: print("    >", ln[:90])
# unique latin tokens
from collections import Counter
toks=Counter()
for ln in latin:
    for t in re.findall(r'[A-Za-z][A-Za-z\-]+', ln):
        toks[t]+=1
print("\n=== top latin tokens ===")
for t,c in toks.most_common(25): print("  %-20s %d"%(t,c))
