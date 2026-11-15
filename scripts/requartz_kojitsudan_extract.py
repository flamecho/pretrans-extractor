#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[JP]Re;quartz零度◆後日談ノベルゲーム 文本提取器 (NW.js + TyranoScript, .ks)

判据（L0，源码级，取自本作 system/builder.ks 宏定义 + 标准 TyranoScript kag.tag.js）：
  - 每个文本框 = [tb_start_text ...] ... [_tb_end_text] 块（宏为空壳，仅分组）
  - #X 行   = 名札（用户要求剔除，不进成品）；# 单独 = 无名边界
  - [p]      = 页界（点击等待 + 清屏）            → 切分新点击段
  - [l]      = 段界（点击等待，不清屏）          → 切分新点击段
  - [lr] 宏  = [l][r]                             → 当作 [l] 切分
  - [r]      = 框内换行（不点击）                → 合并（删标记）
  - [s]      = 文件末 stop 标记                  → 删标记，不切分
  - [ruby text="X"]Y = 振假名，删标记留本体 Y
  - 其余 [标签] 全部删除
  - 一框多次点击（块内 [p]+[l] >=2）→ 双版：先列段行、再列合并行
"""
import os, re, io, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SCN = os.path.join(VNTRANS_HOME, "_work_requartz_kojitsudan/nw/data/scenario")

# 仅抽取主线正文：4 路线 + scene1（序章）。排除系统/菜单/鉴赏。
import glob
MAIN = ["scene1.ks"] + sorted(
    os.path.basename(p)
    for pat in ("sceneALlo_00_*.ks", "sceneAMmn_00_*.ks",
                "sceneANko_00_*.ks", "sceneANnj_00_*.ks")
    for p in glob.glob(os.path.join(SCN, pat))
)

TAG_RE = re.compile(r"\[[^\]]*\]")          # 删除所有 [标签]
SPLIT_RE = re.compile(r"\[(?:p|l)\s*\]")   # [p]/[l] 点击切分（兼容空格）
PAT_NAME = re.compile(r"^#\s*(.*)$")       # 名札行

def clean_part(p):
    p = re.sub(r"\[lr\s*\]", "[l]", p)      # [lr] 宏 → [l]
    parts = SPLIT_RE.split(p)
    out = []
    for i, seg in enumerate(parts):
        # 段内删除所有标签（[r]/[ruby...]/[wait...] 等），留本体
        txt = TAG_RE.sub("", seg)
        out.append(txt)
    return out  # 第 0 段为前段续接；i>0 为被 [p]/[l] 切出的新段

def process_file(path):
    lines = io.open(path, encoding="utf-8").read().split("\n")
    out = []          # 该文件产出的行
    in_block = False
    in_script = False
    segs = []         # [(text, name), ...]
    cur = ""
    cur_name = None
    pending_name = None

    def flush():
        nonlocal cur, cur_name
        if cur.strip() or cur_name:
            segs.append((cur, cur_name))
        cur = ""
        cur_name = None

    for raw in lines:
        st = raw.strip()
        if st.startswith("[iscript]"):
            in_script = True
            continue
        if st.startswith("[endscript]"):
            in_script = False
            continue
        if in_script:
            continue
        if st.startswith("[tb_start_text"):
            in_block = True
            segs = []; cur = ""; cur_name = None; pending_name = None
            continue
        if st.startswith("[_tb_end_text]"):
            if in_block:
                # 块末 flush 最后一段
                if cur.strip() or cur_name:
                    segs.append((cur, cur_name))
                emit(out, segs)
            in_block = False
            continue
        if not in_block:
            continue
        # 名札：用户要求剔除（#X 名字窗 / # 无名边界均跳过）
        if st.startswith("#"):
            continue
        if st.startswith((";", "*", "@")):
            continue
        # 文本行（含点击标记）
        parts = clean_part(raw)
        for i, txt in enumerate(parts):
            if i > 0:
                flush()
                if pending_name is not None:
                    cur_name = pending_name
                    pending_name = None
            # 第一段应用 pending 名札
            if i == 0 and pending_name is not None and not cur:
                cur_name = pending_name
                pending_name = None
            cur += txt
    # 文件结束若仍开块（异常），flush
    if in_block and (cur.strip() or cur_name):
        segs.append((cur, cur_name))
        emit(out, segs)
    return out

CNT_SINGLE = 0
CNT_MULTI = 0
CNT_SEG = 0

def emit(out, segs):
    global CNT_SINGLE, CNT_MULTI, CNT_SEG
    segs = [(t, n) for (t, n) in segs if t.strip() or n]
    if not segs:
        return
    fmt = lambda t, n: t
    if len(segs) == 1:
        CNT_SINGLE += 1
        out.append(fmt(segs[0][0], segs[0][1]))
    else:
        CNT_MULTI += 1
        CNT_SEG += len(segs)
        for t, n in segs:
            out.append(fmt(t, n))
        out.append("".join(fmt(t, n) for t, n in segs))

def main():
    all_lines = []
    for fn in MAIN:
        p = os.path.join(SCN, fn)
        if not os.path.exists(p):
            sys.stderr.write("MISSING %s\n" % fn)
            continue
        all_lines.extend(process_file(p))
    dst = sys.argv[1] if len(sys.argv) > 1 else \
        os.path.join(VNTRANS_HOME, "提取结果/[JP]Re;quartz零度◆後日談ノベルゲーム.txt")
    with io.open(dst, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("\n".join(all_lines) + "\n")
    sys.stderr.write("files=%d lines=%d | 单段块=%d 多段块=%d 段行=%d 合并行=%d\n"
                     % (len(MAIN), len(all_lines), CNT_SINGLE, CNT_MULTI, CNT_SEG, CNT_MULTI))

if __name__ == "__main__":
    main()
