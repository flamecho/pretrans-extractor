#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""DIABOLIK LOVERS LUNATIC PARADE (PSV, PCSG00826) 文本提取

引擎：STCM2L（build "May 18 2015 17:17:25"）—— 与 LOST EDEN **同族**：
逐文件 opcode 重编号（TEXT 本作多为 `0xCBD4`），**点击恒定 `0x1F4`**。

容器链：
  PKG → pkg2zip -x <zRIF> → app/PCSG00826 → psvpfsparser -z <zRIF> -f cma.henkaku.xyz
      → data/STORY.cpk → SCRIPT/{init, scenario/01/{main,sub}, 02, 03, 04, 05}/*.DAT（253 本）
      → data/SYSTEM.cpk → DATABASE/dbSelect.gbin（选项表）

说明：
- 选项表 dbSelect.gbin（GBNB）：104 条 × 64 B 记录（大端 u32 ×16），串区 0x1A40；
  `+0x00` = 组 ID 偏移、`+0x04` = 选项文本偏移 ⇒ 一条记录 = 一个选项。
- `DATABASE/dbDictionary.gbin` 是**薄桜鬼遗留**（新選組 46・土方 12・会津 9，本作相关词 0）⇒ **不收**，本作无用語辞典。
"""
import os
import re
import struct
import sys

CLICK = 0x1F4
JP = re.compile(r"[\u3040-\u30ff]")
KW = re.compile(r"#[A-Za-z][A-Za-z0-9_]*\[[^\]]*\]")
NAME = {"#Name[1]": "小森", "#Name[2]": "ユイ"}


def instrs(d):
    i = d.find(b"CODE_START_")
    if i < 0:
        return []
    o = i + 12
    out = []
    while o + 16 <= len(d):
        ic, op, np_, ln = struct.unpack_from("<IIII", d, o)
        if ln < 16 or ln % 4 or o + ln > len(d) or np_ > 0x100:
            break
        if o + 16 + 12 * np_ > o + ln:
            break
        out.append((o, op, np_, ln))
        o += ln
    return out


# 码位重定义：Rejet/Otomate 这一族把 U+309D/U+309E 当强调标点用（不是叠字本义）
#   ゞ U+309E -> !?   ゝ U+309D -> !!   （半角，与原作标点风格一致）
PUNCT_MAP = str.maketrans({"\u309d": "!!", "\u309e": "!?"})


def fix_punct(s):
    return None if s is None else s.translate(PUNCT_MAP)


def rec(d, p0):
    if not (16 <= p0 <= len(d) - 16):
        return None
    a, b, c, L = struct.unpack_from("<IIII", d, p0)
    if b != L // 4 or c != 1 or L <= 0 or p0 + 16 + L > len(d):
        return None
    try:
        return fix_punct(d[p0 + 16:p0 + 16 + L].split(b"\0")[0].decode("cp932"))
    except UnicodeDecodeError:
        return None


def params(d, o, np_):
    return [struct.unpack_from("<I", d, o + 16 + 12 * k)[0] for k in range(np_)]


def load_select(path, base, rows, stride):
    d = open(path, "rb").read()

    def s(off):
        p = base + off
        e = d.find(b"\0", p)
        return d[p:e].decode("cp932")

    out = {}
    order = []
    for i in range(rows):
        o = i * stride
        gid = s(struct.unpack_from(">I", d, o)[0])
        txt = s(struct.unpack_from(">I", d, o + 4)[0])
        if gid not in out:
            out[gid] = []
            order.append(gid)
        out[gid].append(txt)
    return out


def clean(t):
    for k, v in NAME.items():
        t = t.replace(k, v)
    return KW.sub("", t)


def detect(d, ins, gids):
    score = {}
    selop = None
    for o, op, np_, ln in ins:
        ps = params(d, o, np_)
        if np_ == 1:
            t = rec(d, ps[0])
            if t and JP.search(t) and len(t) >= 10:
                score[op] = score.get(op, 0) + 1
        elif np_ >= 2 and selop is None:
            for q in ps:
                if rec(d, q) in gids:
                    selop = op
                    break
    return (max(score, key=score.get) if score else None), selop


def file_lines(path, sel, stat):
    d = open(path, "rb").read()
    ins = instrs(d)
    if not ins:
        stat["nocode"] += 1
        return []
    text_op, sel_op = detect(d, ins, sel)
    if text_op is None:
        stat["empty"].append(os.path.basename(path))
        return []
    stat["files"] += 1
    stat["op"][text_op] = stat["op"].get(text_op, 0) + 1
    out, cur = [], []
    for o, op, np_, ln in ins:
        if op == text_op:
            ps = params(d, o, np_)
            if not ps:
                continue
            t = rec(d, ps[0])
            stat["text"] += 1
            if t is None:
                stat["fail"] += 1
            elif t.strip("\u3000 "):
                cur.append(t)
        elif op == CLICK:
            stat["click"] += 1
            if cur:
                out.append("".join(cur))
                cur = []
        elif op == sel_op:
            ps = params(d, o, np_)
            gid = next((x for x in (rec(d, p) for p in ps) if x in sel), None)
            stat["sel"] += 1
            if gid:
                if cur:
                    out.append("".join(cur))
                    cur = []
                out.extend(sel[gid])
                stat["selok"] += 1
            else:
                stat["selmiss"] += 1
    if cur:
        out.append("".join(cur))
    return [clean(x) for x in out if clean(x).strip()]


CHAPS = {"cap": 0, "oma": 5, "mini": 1, "Date_with_": 6}


def scene_key(path):
    p = path.replace("\\", "/")
    b = os.path.basename(p)[:-4]
    seg = p.split("/")
    gm = re.match(r"^(\d+)_", seg[-2]) if len(seg) > 1 else None
    grp = int(gm.group(1)) if gm else 99
    if b.startswith("com_prologue"):
        return (0, 0, int(b[-2:]), 0)
    if b.startswith("com_ending"):
        return (1, 99, int(b[-2:]), 0)   # 共通エンド：主线（cap）之后
    if b == "99CERO":
        return (0, 0, 90, 0)          # 路线选择提示，放在序章之后
    if "_mini" in b:
        return (2, grp, int(re.search(r"mini(\d+)", b).group(1)), 0)
    if "_cap" in b:
        return (1, grp, int(re.search(r"cap(\d+)", b).group(1)), 0)
    m = re.match(r"^(\d+)[a-z]+_oma$", b)
    if m:
        return (4, int(m.group(1)), 0, 0)
    if b.startswith("Date_with_"):
        rank = {"SAKAMAKI": 0, "MUKAMI": 1, "TSUKINAMI": 2}
        return (3, rank.get(b[10:], 9), 0, 0)
    return (9, grp, 0, 0)


def main():
    root, out_path, gbin = sys.argv[1], sys.argv[2], sys.argv[3]
    sel = load_select(gbin, 0x1A40, 104, 64)
    files = []
    for r, _, fs in os.walk(root):
        for f in fs:
            if f.upper().endswith(".DAT"):
                files.append(os.path.join(r, f))
    files.sort(key=scene_key)
    stat = {"files": 0, "nocode": 0, "empty": [], "text": 0, "fail": 0,
            "click": 0, "sel": 0, "selok": 0, "selmiss": 0, "op": {}}
    lines = []
    for p in files:
        lines.extend(file_lines(p, sel, stat))
    with open(out_path, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[i] 剧本 {stat['files']}  选项组 {len(sel)}  行 {len(lines)}")
    print(f"[i] text_op {({hex(k): v for k, v in stat['op'].items()})}")
    print(f"[i] TEXT {stat['text']} 失败 {stat['fail']} CLICK {stat['click']} "
          f"SELECT {stat['sel']}（命中 {stat['selok']}/未命中 {stat['selmiss']}）")
    print(f"[i] 无正文文件 {len(stat['empty'])}: {stat['empty'][:8]}")
    print(f"[i] -> {out_path}")


if __name__ == "__main__":
    main()
