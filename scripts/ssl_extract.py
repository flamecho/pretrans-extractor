#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[NS-JP]薄桜鬼SSL ～sweet school life～ 文本提取（STCM2L / Switch / UTF-8）。

容器：romfs/CONTENTS/STORY.cpk（CRI CPK）→ SCRIPT/*.DAT（138 本）＋ SCRIPT/init/*.DAT（4 本系统）。

记录框架（逐文件实测一致，链末 == 头 0x20 的 code_end）：
    [u32 size][参数区…][u32 op][u32 tag][…]
    参数区里的内联字符串 = [u32 0][u32 L/4][u32 1][u32 L][UTF-8 文本][pad]
    tag == 0x12f ⇒ 该记录带字符串参数（op 在 +0x10）
    tag == 1     ⇒ 点击/等待记录（size 固定 0x20，op = 0x10）

op 对照（全库统计：文本恒为 0x125；其余是标签/名札/资源，逐文件编号会变）：
    0x125 TEXT 正文片段（38,684 条，每条恰好 1 个串）
    0x10  CLICK 一次点击（41,879 条，size==0x20 且 tag==1）→ 断框
    其余（0x131/0x132/0x134/0x135/0x137…）＝ sureN 标签 / 名札 / 资源名 ⇒ 丢

用法：
    python scripts/ssl_extract.py <解包目录>/SCRIPT <输出 txt>
"""
import os
import re
import struct
import sys

TEXT_OP = 0x125
CLICK_OP = 0x10

# 主角名（玩家可改名）：#Name[1] 姓 / #Name[2] 名
SURNAME = "雪村"
GIVEN = "千鶴"
NAME_MAP = {"#Name[1]": SURNAME, "#Name[2]": GIVEN}

MACRO = re.compile(r"#[A-Za-z][A-Za-z0-9_]*(?:\[[^\]]*\])?")

# 系统 UI（非正文）：100.DAT 开头的「启动时询问跳过序章」，直接渲染在确认框里
SYSTEM_TEXT = {"プロローグをスキップしますか？"}


def walk(d):
    """按 [u32 size] 走记录链；返回 (记录列表, 链终点)。"""
    u = lambda o: struct.unpack_from("<I", d, o)[0]
    i = d.find(b"CODE_START_")
    if i < 0:
        return [], 0
    o = i + 24
    out = []
    while o + 8 <= len(d):
        sz = u(o)
        if sz <= 0 or sz % 4 or o + sz > len(d):
            break
        out.append((o, sz))
        o += sz
    return out, o


def inline_string(d, off, size):
    """记录内第一个内联字符串（[0][L/4][1][L][utf8]），没有则 None。"""
    u = lambda x: struct.unpack_from("<I", d, x)[0]
    k = 4
    while k < size - 16:
        if u(off + k) == 0 and u(off + k + 4) and u(off + k + 8) == 1:
            L = u(off + k + 12)
            if 0 < L < 4000 and u(off + k + 4) == L // 4 and off + k + 16 + L <= len(d):
                raw = d[off + k + 16:off + k + 16 + L].split(b"\0")[0]
                try:
                    return raw.decode("utf-8")
                except UnicodeDecodeError:
                    return None
        k += 1  # 逐字节扫，允许参数区任意对齐
    return None


def clean(s):
    for k, v in NAME_MAP.items():
        s = s.replace(k, v)
    s = MACRO.sub("", s)          # #Color[n] 之类全部剥掉
    return s


def read_dat(path):
    d = open(path, "rb").read()
    if not d.startswith(b"STCM2L"):
        return []
    recs, _end = walk(d)
    u = lambda x: struct.unpack_from("<I", d, x)[0]
    boxes, cur = [], []
    for off, sz in recs:
        if sz < 0x20:
            continue
        op, tag = u(off + 0x10), u(off + 0x14)
        if tag == 1 and op == CLICK_OP:
            if cur:
                boxes.append("".join(cur))
                cur = []
        elif tag == 0x12F and op == TEXT_OP:
            s = inline_string(d, off, sz)
            if s is None:
                continue
            s = clean(s)
            if not s.strip("\u3000 ") or s in SYSTEM_TEXT:
                continue                     # 整条空行 = 框内占位；系统确认框不入正文
            if cur and s.startswith("\u3000"):
                s = s.lstrip("\u3000")       # 续行行首缩排：并进同一框时去掉
            cur.append(s)
    if cur:
        boxes.append("".join(cur))
    return boxes


def order(fn):
    stem = fn[:-4]
    return (0, 0) if stem == "start" else (1, int(stem)) if stem.isdigit() else (2, stem)


def main(src, out):
    files = sorted((f for f in os.listdir(src) if f.upper().endswith(".DAT")), key=order)
    lines, stats = [], []
    for f in files:
        bs = read_dat(os.path.join(src, f))
        lines.extend(bs)
        stats.append("%s\t%d" % (f, len(bs)))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8-sig", newline="\n") as fh:
        for ln in lines:
            fh.write(ln + "\n")
    with open(os.path.join(os.path.dirname(os.path.abspath(src)), "stats.tsv"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(stats))
    print("脚本 %d / 行 %d / 字节 %d" % (len(files), len(lines), os.path.getsize(out)))


if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[3] if len(a) > 3 else a[2])
