#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""DIABOLIK LOVERS LOST EDEN (PSV, PCSG00910) 文本提取

引擎：STCM2L（build "May 18 2015 17:17:25"）—— **每文件 opcode 重编号**（同 Norn9 族），
故 text_op / select_op 逐文件检测；点击 op 恒定 `0x1F4`。

容器链：
  PKG → pkg2zip -x <zRIF> → app/PCSG00910 → psvpfsparser -z <zRIF> -f cma.henkaku.xyz
      → data/STORY.cpk → SCRIPT/{init,scenario/<NN>_<chara>}/*.DAT（552 本剧本）
      → data/SYSTEM.cpk → DATABASE/dbSelect.gbin（选项表）・dbSpeaker.gbin（说话人表）

脚本格式：
  "STCM2L May 18 2015 17:17:25\0" + GLOBAL_DATA + CODE_START_ → 指令流 = CODE_START_+12
  指令 = [u32 is_call][u32 opcode][u32 nparams][u32 length] + np×[p0][0x40000000][0x40000000]
  文本记录 = [u32 0][u32 L/4][u32 1][u32 L][cp932][pad]

选项表 dbSelect.gbin（GBNB）：782 条 × 68 B 大端记录 ＋ 串区 0xD010；
  +0x00 = 组 ID 偏移、+0x04 = 选项文本偏移（文本去重，同串可复用）⇒ 一条记录 = 一个选项。

成行（L0）：两次 0x1F4 之间的全部 text_op 记录 = 一屏 = 一行；纯全角空格记录 = 排版空行，丢弃。
说话人：dbSpeaker.gbin 按 id 取名（名字窗独立）⇒ 不输出。
"""
import os
import re
import struct
import sys

CLICK = 0x1F4
JP = re.compile(r"[\u3040-\u30ff]")
KW = re.compile(r"#[A-Za-z][A-Za-z0-9_]*\[[^\]]*\]")
NAME = {"#Name[1]": "小森", "#Name[2]": "ユイ"}

SEL_BASE, SEL_ROWS, SEL_STRIDE = 0xD010, 782, 68

# 章节顺序（同系列的开发方编号：DARK → MANIAC → ECSTASY → HEAVEN → ED）
CHAP = {"dark": 0, "maniac": 1, "ecstasy": 2, "heaven": 3, "ed": 4}
CHARA = {"aya": 0, "kana": 1, "lai": 2, "shu": 3, "reiji": 4, "sub": 5, "ruki": 6,
         "kou": 7, "yuma": 8, "azusa": 9, "carla": 10, "shin": 11, "kino": 12}


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


def load_select(path):
    d = open(path, "rb").read()

    def s(off):
        p = SEL_BASE + off
        e = d.find(b"\0", p)
        return d[p:e].decode("cp932")

    out = {}
    for i in range(SEL_ROWS):
        o = i * SEL_STRIDE
        gid = s(struct.unpack_from(">I", d, o)[0])
        txt = s(struct.unpack_from(">I", d, o + 4)[0])
        out.setdefault(gid, []).append(txt)
    return out


def clean(t):
    for k, v in NAME.items():
        t = t.replace(k, v)
    return KW.sub("", t)


def detect(d, ins, gids):
    """逐文件检测 text_op（长日文最多者）与 select_op（参数命中组 ID 者）。"""
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
    text_op = max(score, key=score.get) if score else None
    return text_op, selop


def file_lines(path, sel, stat):
    d = open(path, "rb").read()
    ins = instrs(d)
    if not ins:
        stat["nocode"] += 1
        return []
    text_op, sel_op = detect(d, ins, sel)
    if text_op is None:
        stat["empty"] += 1
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


def scene_key(path):
    b = os.path.basename(path)[:-4]                   # LE_aya_dark_00
    d = os.path.basename(os.path.dirname(path))       # 01_aya
    m = re.match(r"^(\d+)_", d)
    dnum = int(m.group(1)) if m else 99
    if b.startswith("LE_prologue_"):
        return (dnum, -1, int(b.rsplit("_", 1)[1]))
    m = re.match(r"^LE_[a-z]+_(dark|maniac|ecstasy|heaven|ED)(\d*)$", b)
    if m:
        return (dnum, CHAP.get(m.group(1).lower(), 9), int(m.group(2) or 0))
    return (dnum, 8, 0)


def main():
    src, out_path, gbin = sys.argv[1], sys.argv[2], sys.argv[3]
    sel = load_select(gbin)
    files = []
    for root, _, fs in os.walk(src):
        for f in fs:
            if f.upper().endswith(".DAT"):
                files.append(os.path.join(root, f))
    files.sort(key=scene_key)
    stat = {"files": 0, "nocode": 0, "empty": 0, "text": 0, "fail": 0,
            "click": 0, "sel": 0, "selok": 0, "selmiss": 0, "op": {}}
    lines = []
    for p in files:
        lines.extend(file_lines(p, sel, stat))
    with open(out_path, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[i] 剧本文件 {stat['files']}（无 CODE {stat['nocode']} / 无正文 {stat['empty']}）"
          f"  选项组 {len(sel)}  行 {len(lines)}")
    print(f"[i] text_op 分布 { {hex(k): v for k, v in stat['op'].items()} }")
    print(f"[i] TEXT {stat['text']} 失败 {stat['fail']}  CLICK {stat['click']}  "
          f"SELECT {stat['sel']}（命中 {stat['selok']} / 未命中 {stat['selmiss']}）")
    print(f"[i] -> {out_path}")


if __name__ == "__main__":
    main()
