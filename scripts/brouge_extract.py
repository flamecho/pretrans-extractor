# -*- coding: utf-8 -*-
"""Butterfly Rouge (PC / WillPlus-AdvHD) text extractor.

Source disc : DKRDISC1.ISO  (UDF, no encryption)
Script arc  : Rio.arc       (ext-group container, 182 x WSC; 151 x BR_* story)
Engine      : WillPlus / AdvHD   (see scripts/advhd.py)

Output      : 提取结果/Butterfly Rouge_全文本.txt
                 narration (op41) + dialogue (op42) + choices (op02)
                 one message box == one line ; UTF-8 BOM ; pure LF

Usage:
    python scripts/brouge_extract.py _work_brouge/Rio.arc 提取结果
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import advhd

STORY_RE = re.compile(r'^BR_(\d+)')          # story scripts: BR_00 .. BR_30OMAKE

def order_key(name):
    m = STORY_RE.match(name)
    return int(m.group(1)) if m else -1       # -1 => excluded (system/UI scripts)

# --- 原作脚本笔误的「按作者意图」修正（显式、可回溯；逐条经原始字节码核对）---
# 3 处均非提取缺陷：引号数量在原始 WSC 中即不配对，唯一合理解读如下。
POSTFIX = {
    # BR_03G  op42  原: ...です」」  (81 76 81 76)   -> 多一个右书名号
    '「出来るかどうかじゃなくて、やりたいんです」」':
        '「出来るかどうかじゃなくて、やりたいんです」',
    # BR_05R  op42  原: ...でした」」  (81 76 81 76)  -> 多一个右书名号
    '「うん。また明日。お疲れさまでした」」':
        '「うん。また明日。お疲れさまでした」',
    # BR_24END01 op41  原: でも、…夫婦になる）  -> 内心独白，缺起始 （
    'でも、それを乗り越えて私達は今日、夫婦になる）':
        '（でも、それを乗り越えて私達は今日、夫婦になる）',
}

def main():
    arc = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else '提取结果'
    lines = advhd.extract_arc(arc, order_key)
    fixed = 0
    for i, l in enumerate(lines):
        if l in POSTFIX:
            lines[i] = POSTFIX[l]
            fixed += 1
    print("source-typo fixes applied:", fixed)
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, "Butterfly Rouge_全文本.txt")
    advhd.write_txt(out, lines)
    print("lines:", len(lines), "->", out)

if __name__ == '__main__':
    main()
