#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ORPHAN DRUG (FUSYRO / KiriKiri KAG3) 文本提取
- 容器: 自解压 RAR5 -> data.xp3 (XP3) -> scenario/*.ks
- 文本判据(L0): [p] = 一框/一次点击边界; [locate x=130 y=240|310]TEXT = 选项标签
- 名札: [SAT]/[SAK] 宏在消息框内联打印名字(无独立名窗) -> 保留并接在台词前
- 历史层装饰(HSP/HHH/HLL/HLN/HMAK/HMES) -> 仅 backlog, 不上屏 -> 丢弃
"""
import re, os

SRC = "ks/scenario_act001.ks"
OUT = "out/[JP]ORPHAN DRUG.txt"

# 名字宏 -> 内联文本(宏体: [nowait]　名[endnowait][r]), 名札用【】包裹
NAME_MACRO = {
    "SAT": "【砂終戒】",
    "SAK": "【九鬼朔耶】",
}
# 仅历史层显示的装饰宏(char=false / graph alt= / storage=sys_hislay) -> 不上屏
HISTORY_ONLY = {"HSP", "HHH", "HLN", "HLL", "HMAK", "HMES"}

jp = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
loc_re = re.compile(r'\[locate x=130 y=(?:240|310)\]([^\[\]\r\n]+)')

def clean_box(s: str) -> str:
    # 1) 名字宏展开为内联文本
    for k, v in NAME_MACRO.items():
        s = s.replace("[" + k + "]", v)
    # 2) 历史层装饰宏 -> 空
    for m in HISTORY_ONLY:
        s = s.replace("[" + m + "]", "")
    # 3) 剥离所有其余命令标签 [tag ...]
    s = re.sub(r'\[[^\]]*\]', '', s)
    # 4) 框内换行/回车合并(一次点击=一行)
    s = s.replace('\r', '').replace('\n', '')
    # 5) 去除首尾空白(保留名字宏内的全角空格等正文)
    return s.strip()

def extract():
    raw = open(SRC, "rb").read().decode("cp932", "replace")
    lines = raw.split('\n')
    out = []
    buf = []

    def flush():
        if buf:
            t = clean_box(''.join(buf))
            if t:
                out.append(t)
            buf.clear()

    for line in lines:
        line = line.rstrip('\r')
        # 注释行
        if line.lstrip().startswith(';'):
            continue
        if not line.strip():
            continue
        # KAG 标签行(*name 或 *name|caption): 行首 '*' 起头
        if line.lstrip().startswith('*'):
            if '[' not in line:
                # 纯标签行(仅跳转/场景标题) -> 不上屏, 丢弃
                continue
            # 内联标签(标签后跟命令/正文) -> 剥掉行首标签前缀, 保留其余
            line = re.sub(r'^\s*(\*[^\s\[]*\|?)+', '', line)
        # 选项标签: [locate x=130 y=240|310]TEXT
        m = loc_re.search(line)
        if m and m.group(1).strip():
            flush()
            out.append(m.group(1).strip())
            continue
        # 按钮(无文本) -> 跳过
        if '[button' in line:
            continue
        # [p] = 框边界
        if '[p]' in line:
            parts = line.split('[p]')
            for k, part in enumerate(parts):
                buf.append(part)
                if k < len(parts) - 1:
                    flush()
        else:
            buf.append(line)
    flush()
    return out

def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    lines = extract()
    # 输出: UTF-8 BOM + LF
    with open(OUT, "w", encoding="utf-8-sig", newline="\n") as f:
        for l in lines:
            f.write(l + "\n")
    print("lines written:", len(lines))
    # 统计
    from collections import Counter
    c = Counter()
    for l in lines:
        if loc_re.search(l) or l in [v.strip() for v in NAME_MACRO.values()]:
            pass
    # 简单分类: 含名字前缀 vs 选项 vs 普通
    choice = sum(1 for l in lines if any(l == t.strip() for t in NAME_MACRO.values()))
    print("sample (first 12):")
    for l in lines[:12]:
        print("  ", repr(l))
    print("last 4:")
    for l in lines[-4:]:
        print("  ", repr(l))

if __name__ == "__main__":
    main()
