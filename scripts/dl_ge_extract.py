#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""DIABOLIK LOVERS GRAND EDITION for Nintendo Switch —— 文本提取。

引擎：Bezel（Switch 中间件）+ 自定义 STCM2L 2012 指令流（idea-factory 血统）。

容器链：
  romfs/script.cpk (CRI CPK) → SCRIPT/*.dat ×706（433 mb_ + 272 ve_ + start）
  romfs/Archive/static~select.bin.nxonnx32.bea → SCNE/ASST0 + zstd → BIN_ 选项表

脚本结构（实测）：
  头 32B generator("STCM2L Aug 24 2012 …") + "GLOBAL_DATA\0" + globals
  "CODE_START_\0" (12B) → 指令流起点 = CODE_START_ 偏移 + 12
  指令 = [u32 is_call][u32 opcode][u32 nparams][u32 length] + np×[u32 p0][0x40000000][0x40000000]
  文本记录（p0 指向）= [u32 0][u32 L/4][u32 1][u32 L][cp932 文本][pad→4]

opcode（全 706 文件一致）：
  0x4BA TEXT  0x4BB WAIT(一次点击)  0x4BC 说话人 ID（独立名字窗 ⇒ 不输出）
  0x599 select(选项组 ID)  0x44E sureN  0x41B/0x41C/0x41D switch

成行判据 L0：两次 0x4BB 之间的全部 0x4BA ＝ 一屏 ＝ 一行。
选项表：501 组 × 2 条，key 区（组 ID 成对）+ 文本区（1002 条）；
       组 g 的选项 = texts[2g], texts[2g+1]（逐条语义成对，已全量核对）。
"""
import os
import re
import sys
import struct

TEXT, WAIT, SPEAK, SELECT = 0x4BA, 0x4BB, 0x4BC, 0x599

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
        out.append((o, ic, op, np_, ln))
        o += ln
    return out


# 码位重定义：Rejet/Otomate 这一族把 U+309D/U+309E 当强调标点用（不是叠字本义）
#   ゞ U+309E -> !?   ゝ U+309D -> !!   （半角，与原作标点风格一致）
PUNCT_MAP = str.maketrans({"\u309d": "!!", "\u309e": "!?"})


def fix_punct(s):
    return None if s is None else s.translate(PUNCT_MAP)


def rec(d, p0):
    n = len(d)
    if not (16 <= p0 <= n - 16):
        return None
    a, b, c, L = struct.unpack_from("<IIII", d, p0)
    if b != L // 4 or c != 1 or L <= 0 or p0 + 16 + L > n:
        return None
    try:
        return fix_punct(d[p0 + 16:p0 + 16 + L].split(b"\0")[0].decode("cp932"))
    except UnicodeDecodeError:
        return None


def params(d, o, np_):
    return [struct.unpack_from("<I", d, o + 16 + 12 * k)[0] for k in range(np_)]


# ---------- 选项表 ----------
def load_select(bea_path):
    import zstandard as zstd
    d = open(bea_path, "rb").read()
    i = d.find(b"\x28\xb5\x2f\xfd")
    out = zstd.ZstdDecompressor().decompress(d[i:])
    assert out[:4] == b"BIN_", out[:8]
    idx_off = struct.unpack_from("<I", out, 0x14)[0]
    str_off = struct.unpack_from("<I", out, 0x18)[0]
    cnt = (str_off - idx_off) // 4
    idx = [struct.unpack_from("<I", out, idx_off + 4 * k)[0] for k in range(cnt)]

    def s(n):
        o = str_off + idx[n]
        e = out.find(b"\0", o)
        return out[o:e].decode("cp932")

    # 1..1002 = key（组 ID，成对），1003..2004 = 选项文本
    keys = [s(n) for n in range(1, 1003)]
    texts = [s(n) for n in range(1003, 2005)]
    m = {}
    for g in range(len(texts) // 2):
        m[keys[2 * g]] = (texts[2 * g], texts[2 * g + 1])
    return m


# ---------- 正文 ----------
def clean(t):
    for k, v in NAME.items():
        t = t.replace(k, v)
    return KW.sub("", t)


def file_lines(path, sel):
    d = open(path, "rb").read()
    out = []
    cur = []
    for o, ic, op, np_, ln in instrs(d):
        if op == TEXT:
            t = rec(d, params(d, o, np_)[0])
            if t is not None and t.strip("\u3000 "):
                cur.append(t)
        elif op == SELECT:
            ps = [rec(d, p) for p in params(d, o, np_)]
            gid = next((x for x in ps if x and x != "select"), None)
            if gid in sel:
                if cur:
                    out.append("".join(cur))
                    cur = []
                out.extend(sel[gid])
        elif op == WAIT:
            if cur:
                out.append("".join(cur))
                cur = []
    if cur:
        out.append("".join(cur))
    return [clean(x) for x in out if clean(x).strip()]


# 作品：ve_ = 本篇（Haunted dark bridal，2012）／mb_ = MORE,BLOOD（2013）
# 判据：ve_aya_Dark_00 开头「はぁ、誰もいなくなっちゃった。」＝本篇女主放学独白；
#       mb_aya_Dark_00 开头「高く、どこまでも高く、積み木を重ねていく。」＝MB 开场。
WORK = {"ve": 0, "mb": 1}
# 角色序（逆巻六兄弟 → 無神家）
CHARA = {"aya": 0, "kan": 1, "lai": 2, "shu": 3, "rei": 4, "sub": 5,
         "ruk": 6, "kou": 7, "yum": 8, "azu": 9}
# 章节序（剧情顺序）
CHAP = {"Dark": 0, "Ecstasy": 1, "Maniac": 2, "Heaven": 3, "After": 4, "ED": 5}


def scene_key(fn):
    b = fn[:-4]
    m = re.match(r"^(mb|ve)_prologue_(\d+)$", b)
    if m:
        return (WORK[m.group(1)], -1, 0, 0, 0, int(m.group(2)))
    m = re.match(r"^(mb|ve)_(sub_)?([a-z]+)_([A-Za-z]+)_(\d+)", b)
    if m:
        w = WORK[m.group(1)]
        # `ve_sub_*` = 本篇里スバル的另一套（sub 与前缀同义），按角色 sub 处理
        ch = m.group(3)
        return (w, 1, CHARA.get(ch, 99), CHAP.get(m.group(4), 99), 0, int(m.group(5)))
    return (3, 9, 99, 99, 0, 0)


def main():
    src, out_path, bea = sys.argv[1], sys.argv[2], sys.argv[3]
    sel = load_select(bea)
    files = sorted((f for f in os.listdir(src) if f.lower().endswith(".dat")), key=scene_key)
    lines = []
    for fn in files:
        lines.extend(file_lines(os.path.join(src, fn), sel))
    with open(out_path, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[i] 文件 {len(files)}  选项组 {len(sel)}  行 {len(lines)} -> {out_path}")


if __name__ == "__main__":
    main()
