#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""DIABOLIK LOVERS DARK FATE (PSV, PCSG00530) 文本提取

引擎：STCM2L（build "Oct  8 2014 15:50:16"）＋ Bezel 血统 op 体系
  （与 Switch 版 DIABOLIK LOVERS GRAND EDITION 同族：0x4BA 文本 / 0x4BB 点击 /
    0x4BC 说话人 ID / 0x599 选项组 / 0x5A8 清屏）

容器链：
  PKG → pkg2zip -x → <zRIF> → app/PCSG00530 → psvpfsparser -z <zRIF> -f cma.henkaku.xyz
      → data/GAME.cpk → script/*.DAT（522 本）＋ database/data/*.gbin

脚本格式（字节级）：
  "STCM2L Oct  8 2014 15:50:16\0" + u32 + GLOBAL_DATA + CODE_START_
  指令流起点 = CODE_START_ 偏移 + 12
  指令 = [u32 is_call][u32 opcode][u32 nparams][u32 length] + np×[p0][0x40000000][0x40000000]
  文本记录 = [u32 0][u32 L/4][u32 1][u32 L][cp932][pad]

选项表 database/data/dbXlsSelect.gbin（GBNB 容器）：
  记录区 723 条 × 64 B，字段为大端 u32：
    +0x00 = 组 ID 串偏移（串区基址 0xb500）
    +0x04 = 选项文本串偏移
    +0x38 = 该组选项数（部分记录为 0，按出现顺序累计即可）
  一条记录 = 一个选项；按组 ID 分组即得 361 组（360×2 ＋ 1×3）。

成行（L0）：两次 0x4BB 之间的全部 0x4BA = 一屏 = 一行；屏内 0x5A8 实测 0 次（不承担分屏）。
说话人：0x4BC 指向 1 字节 ID（0=无）⇒ 名字窗独立，不输出。
"""
import os
import re
import struct
import sys

TEXT, WAIT, SPEAK, SELECT, CLEAR = 0x4BA, 0x4BB, 0x4BC, 0x599, 0x5A8

KW = re.compile(r"#[A-Za-z][A-Za-z0-9_]*\[[^\]]*\]")
NAME = {"#Name[1]": "小森", "#Name[2]": "ユイ"}

# 非正文：系统初始化 / 表情表 / 测试与样例
SKIP = {"0-init.DAT", "1-i_back.DAT", "2-i_chara.DAT", "3-i_flag.DAT",
        "4-i_movie.DAT", "5-i_effect.DAT", "991.DAT", "992.DAT", "993.DAT",
        "994.DAT", "995.DAT", "996.DAT", "1000_novel_sample.DAT", "1010_test.DAT"}


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
        out.append((o, ic, op, np_, ln))
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


def speaker_id(d, p0):
    """0x4BC 参数指向 [0][1][1][4] ＋ 1 字节角色 ID（0 = 无名札）。"""
    if not (16 <= p0 < len(d) - 16):
        return None
    return d[p0 + 16]


# ---------- 选项表 ----------
def load_select(gbin_path, base=0xB500, rows=723, stride=64):
    d = open(gbin_path, "rb").read()

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


# ---------- 正文 ----------
def file_lines(path, sel, stat):
    d = open(path, "rb").read()
    out = []
    cur = []
    for o, ic, op, np_, ln in instrs(d):
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
        elif op == WAIT:
            stat["wait"] += 1
            if cur:
                out.append("".join(cur))
                cur = []
        elif op == CLEAR:
            stat["clear"] += 1
    if cur:
        out.append("".join(cur))
    return [clean(x) for x in out if clean(x).strip()]


def scene_key(fn):
    m = re.match(r"^(\d+)", fn)
    return (int(m.group(1)) if m else 9999, fn)


def main():
    src, out_path, gbin = sys.argv[1], sys.argv[2], sys.argv[3]
    sel = load_select(gbin)
    files = sorted((f for f in os.listdir(src) if f.upper().endswith(".DAT")),
                   key=scene_key)
    stat = {"text": 0, "fail": 0, "wait": 0, "clear": 0, "sel": 0,
            "selok": 0, "selmiss": []}
    lines = []
    used = 0
    for fn in files:
        if fn in SKIP:
            continue
        got = file_lines(os.path.join(src, fn), sel, stat)
        used += 1
        lines.extend(got)
    with open(out_path, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[i] 文件 {used}/{len(files)}  选项组 {len(sel)}  行 {len(lines)}")
    print(f"[i] TEXT {stat['text']}  解析失败 {stat['fail']}  WAIT {stat['wait']}  "
          f"CLEAR {stat['clear']}  SELECT {stat['sel']}（命中 {stat['selok']}）")
    if stat["selmiss"]:
        miss = [x for x in dict.fromkeys(stat["selmiss"]) if x]
        print(f"[!] 未命中组 {len(miss)}: {miss[:8]}")
    print(f"[i] -> {out_path}")


if __name__ == "__main__":
    main()
