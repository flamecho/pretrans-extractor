#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""DIABOLIK LOVERS VANDEAD CARNIVAL (PSV, PCSG00472) 文本提取

引擎：STCM2L（build "Jul 12 2010 10:20:01"）—— 与 DARK FATE **同族**（Bezel 血统 op），
op 恒定：`0x4BA` 文本 / `0x4BB` 点击 / `0x4BC` 说话人(1 字节 ID) / `0x599` 选项组 / `0x5A8` 清屏。

容器链：
  PKG → pkg2zip -x <zRIF> → app/PCSG00472 → psvpfsparser -z <zRIF> -f cma.henkaku.xyz
      → data/GAME.cpk → script/1-scenario/**/*.DAT（154 本）＋ script/99-CERO（表情/调试样例）
                     → database/data/dbXlsSelect.gbin（选项表）

选项表 dbXlsSelect.gbin（GBNB）：84 条 × 56 B（大端 u32 ×14），串区 0x12A0；
  `+0x00` = 组 ID 偏移、`+0x04` = 选项文本偏移 ⇒ 一条记录 = 一个选项（42 组 × 2）。
"""
import os
import re
import struct
import sys

TEXT, WAIT, SPEAK, SELECT, CLEAR = 0x4BA, 0x4BB, 0x4BC, 0x599, 0x5A8
JP = re.compile(r"[\u3040-\u30ff]")
KW = re.compile(r"#[A-Za-z][A-Za-z0-9_]*\[[^\]]*\]")
NAME = {"#Name[1]": "小森", "#Name[2]": "ユイ"}

SEL_BASE, SEL_ROWS, SEL_STRIDE = 0x12A0, 84, 56


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


def load_select(path, base=SEL_BASE, rows=SEL_ROWS, stride=SEL_STRIDE):
    d = open(path, "rb").read()

    def s(off):
        p = base + off
        e = d.find(b"\0", p)
        return d[p:e].decode("cp932")

    out = {}
    for i in range(rows):
        o = i * stride
        gid = s(struct.unpack_from(">I", d, o)[0])
        txt = s(struct.unpack_from(">I", d, o + 4)[0])
        out.setdefault(gid, []).append(txt)
    return out


def clean(t):
    for k, v in NAME.items():
        t = t.replace(k, v)
    return KW.sub("", t)


def file_lines(path, sel, stat):
    d = open(path, "rb").read()
    ins = instrs(d)
    if not ins:
        stat["nocode"] += 1
        return []
    out, cur = [], []
    for o, op, np_, ln in ins:
        if op == TEXT:
            ps = params(d, o, np_)
            if not ps:
                continue
            t = rec(d, ps[0])
            stat["text"] += 1
            if t is None:
                stat["fail"] += 1
            elif t.strip("\u3000 "):
                cur.append(t)
        elif op == WAIT:
            stat["click"] += 1
            if cur:
                out.append("".join(cur))
                cur = []
        elif op == SELECT:
            ps = params(d, o, np_)
            ids = [rec(d, p) for p in ps]
            gid = next((x for x in ids if x and x != "select"), None)
            stat["sel"] += 1
            if gid in sel:
                if cur:
                    out.append("".join(cur))
                    cur = []
                out.extend(sel[gid])
                stat["selok"] += 1
            else:
                stat["selmiss"].append(gid)
        elif op == CLEAR:
            stat["clear"] += 1
    if cur:
        out.append("".join(cur))
    return [clean(x) for x in out if clean(x).strip()]


def scene_key(path):
    b = os.path.basename(path)
    m = re.match(r"^(\d+)", b)
    n = int(m.group(1)) if m else 9999
    if n == 101:            # 序章（101-prologue_all）
        return (0, 0, n)
    if n == 102:            # 共通エンド（102-ending_all）：主线之后
        return (2, 0, n)
    if 200 <= n < 300:      # 主线 cap/finale
        return (1, n, n)
    if 300 <= n < 400:      # サブシナリオ
        return (3, n, n)
    if 400 <= n < 600:      # Presents（逆巻／無神）
        return (4, n, n)
    if n >= 600:            # 個別エピローグ
        return (5, n, n)
    return (9, n, n)


def main():
    root, out_path, gbin = sys.argv[1], sys.argv[2], sys.argv[3]
    sel = load_select(gbin)
    files = []
    for r, _, fs in os.walk(root):
        for f in fs:
            if f.upper().endswith(".DAT"):
                files.append(os.path.join(r, f))
    files.sort(key=scene_key)
    stat = {"nocode": 0, "text": 0, "fail": 0, "click": 0, "sel": 0,
            "selok": 0, "selmiss": [], "clear": 0}
    lines = []
    for p in files:
        lines.extend(file_lines(p, sel, stat))
    with open(out_path, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[i] 文件 {len(files)}  选项组 {len(sel)}  行 {len(lines)}")
    print(f"[i] TEXT {stat['text']} 失败 {stat['fail']}  CLICK {stat['click']}  "
          f"CLEAR {stat['clear']}  SELECT {stat['sel']}（命中 {stat['selok']}）")
    if stat["selmiss"]:
        print(f"[!] 未命中: {stat['selmiss'][:8]}")
    print(f"[i] -> {out_path}")


if __name__ == "__main__":
    main()
