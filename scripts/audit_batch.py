#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批次审计：① 变量/宏错误填充残留  ② 双版对照断行位置自洽性
用法：
  python scripts/audit_batch.py vars            # 全成品残留扫描
  python scripts/audit_batch.py dual <file>     # 单部双版断行验证
输出均控制在 80 行内。
"""
import sys, os, re, glob, unicodedata

RES = "提取结果"

# 可疑模式：名字 → 正则（都按「出现即须人工判定」处理，除注明）
PATS = [
    ("未解析",     r"〔未解析〕"),
    ("〓",         r"〓"),
    ("FFFD",       r"\ufffd"),
    ("半角假名",   r"[\uff66-\uff9f]"),
    ("控制符",     r"[\x00-\x08\x0b\x0c\x0e-\x1f]"),
    ("%s类",       r"%[sdr@]"),
    ("name-x",     r"(?i)\[name\d?\]|%name%|\{name\}|<name>"),
    ("宏$残留",    r"[%$][A-Za-z_]{2,}"),
    ("@标签",      r"<[a-zA-Z/][^>\n]{0,20}>"),
    ("反斜杠n",    r"\\n|\\t"),
    ("&符",        r"&(?!amp;|lt;|gt;|quot;)"),
    ("锐括号",     r"[<>]"),
    ("花括号",     r"[{}]"),
    ("圈点占位",   r"[○●◯◻□■〈〉《》]"),
    ("拉丁行",     r"^[ -~]+$"),
]

def vars_scan():
    rows = []
    for f in sorted(glob.glob(os.path.join(RES, "*.txt"))):
        name = os.path.basename(f)[:-4]
        txt = open(f, encoding="utf-8-sig").read()
        lines = txt.split("\n")
        cnt = {}
        for label, pat in PATS:
            n = len(re.findall(pat, txt, re.M))
            if n:
                cnt[label] = n
        rows.append((name, len(lines), cnt))
    # 表头 + 仅列非零项
    print(f"{'作品':<46} {'行数':>7}  非零项")
    for name, nl, cnt in rows:
        s = " ".join(f"{k}={v}" for k, v in cnt.items()) or "—"
        print(f"{name[:46]:<46} {nl:>7}  {s}")
    print(f"\n共 {len(rows)} 部。判定原则：原文自带（英文行/半角标点/圈点排版）登记 allow，"
          f"残留（@标签、%s、&、\\n、宏$）须回溯脚本修正。")

def dual_check(path):
    txt = open(path, encoding="utf-8-sig").read()
    lines = txt.split("\n")
    n = len(lines)
    # 合并行：本行 == 上方 2..4 行顺序拼接（无分隔符）；同时记录有多少段
    merge = []          # (idx, k)
    for i in range(2, n):
        cur = lines[i]
        if not cur:
            continue
        for k in (4, 3, 2):          # 优先取最长匹配（4 段）
            if i - k < 0:
                continue
            seg = lines[i-k:i]
            if any(len(x) == 0 for x in seg):
                continue
            if "".join(seg) == cur:
                merge.append((i, k))
                break
    # 段行：被合并行覆盖的那些
    covered = set()
    for i, k in merge:
        for j in range(i-k, i):
            covered.add(j)
    # 连续段组（未被覆盖的相邻两行以上）＝可能的漏合并/断框错位
    groups = []
    i = 0
    while i < n:
        if i not in covered and lines[i] and i + 1 < n and (i+1) not in covered and lines[i+1]:
            k = 1
            while i + k < n and (i+k) not in covered and lines[i+k]:
                k += 1
            if k >= 2:
                groups.append((i, k))
                i += k
                continue
        i += 1
    print(f"=== {os.path.basename(path)} ===")
    print(f"行数 {n}／合并行 {len(merge)}（段数分布 "
          f"{ {k: sum(1 for _, kk in merge if kk == k) for k in (2,3,4)} }）／被覆盖段行 {len(covered)}")
    if len(merge) == 0:
        print("[!] 未检出任何「逐字等于上方拼接」的合并行 —— 若本作标称双版，断行口径可疑")
    # 校验：合并行内容是否真的是「逐字」相等（上面已是严格相等）
    print(f"[i] 合并行严格逐字相等的比例：{len(merge)}/{len(merge)} = 100%" if merge else "[i] n/a")
    print(f"[?] 未被合并的连续段组 {len(groups)} 处（≥2 行相邻正文）：")
    for i, k in groups[:8]:
        head = " | ".join(x[:26] for x in lines[i:i+k])
        print(f"    L{i+1} ×{k}: {head[:120]}")
    if len(groups) > 8:
        print(f"    … 另 {len(groups)-8} 处")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
    elif sys.argv[1] == "vars":
        vars_scan()
    elif sys.argv[1] == "dual":
        for p in sys.argv[2:]:
            dual_check(p)
