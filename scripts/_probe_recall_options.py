# -*- coding: utf-8 -*-
"""Recall 选项/系统文件深度探针。"""
import os, re, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xp3 import XP3
from recall_extract import read_ks, parse_kag

XP3_PATH = os.path.join(VNTRANS_HOME, "_work_recall/src/[JP]Recall/data.xp3")
xp3 = XP3(XP3_PATH)
ks = sorted(n for n in xp3.files if n.lower().endswith('.ks'))

# ---- A. 真实 parse_kag 统计：哪些 .ks 产 0 box ----
print("=== 真实 parse_kag：0-box 文件清单 ===")
zero = []
for name in ks:
    t = read_ks(xp3, name)
    if not t.strip():
        zero.append((name, 'RAW_EMPTY', 0, 0)); continue
    boxes, opts = parse_kag(t)
    ja = len(re.findall(r'[\u3040-\u30ff\u4e00-\u9fff]', t))
    nscript = len(re.findall(r'\[iscript|@iscript|\[endscript', t, re.I))
    nmacro = len(re.findall(r'\[macro|@macro|@defmacro|function\s+\w+|@eval', t, re.I))
    if len(boxes) == 0:
        zero.append((name, f'ja={ja},script={nscript},macro={nmacro}', ja, nscript))
print(f"  0-box 文件数: {len(zero)} / 总 {len(ks)}")
for nm, tag, ja, sc in zero:
    print(f"  {tag:40} {nm}")

# ---- B. 选项形态：button / ch / choice 上下文 ----
print("\n=== [button 上下文（前 3 例）===")
cnt=0
for name in ks:
    t = read_ks(xp3, name)
    for m in re.finditer(r'.{0,40}\[button.{0,100}', t, re.I|re.S):
        print(f"[{name}] {m.group(0).replace(chr(10),'\\\\n')}")
        cnt+=1; break
    if cnt>=3: break

print("\n=== [ch 上下文（前 3 例）===")
cnt=0
for name in ks:
    t = read_ks(xp3, name)
    for m in re.finditer(r'.{0,60}\[ch\b.{0,80}', t, re.I|re.S):
        print(f"[{name}] {m.group(0).replace(chr(10),'\\\\n')}")
        cnt+=1; break
    if cnt>=3: break

print("\n=== [choice 上下文（前 3 例）===")
cnt=0
for name in ks:
    t = read_ks(xp3, name)
    for m in re.finditer(r'.{0,60}\[choice\b.{0,80}', t, re.I|re.S):
        print(f"[{name}] {m.group(0).replace(chr(10),'\\\\n')}")
        cnt+=1; break
    if cnt>=3: break
