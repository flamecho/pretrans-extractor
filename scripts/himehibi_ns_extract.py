#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ひめひび -Princess Days-（NS-JP, 0100F8D0129F4000）全文本提取。

Takuyo gss / Switch 变体：
  romfs/SCRDATA.BIN = LSDARC V.100 索引（531 条，全 isPacked=0）
  romfs/SCRDATA.ARC = 脚本数据，头 "SCR 3.00"
  SCR 3.00 指令：u16 op | u16 size(总长含 6B 头) | u16 id | operand*<u8 type><data>
文本 op：0x5a 正文 / 0xfc 带 %s 正文（源＝后随 type6 槽）/ 0xf0 扉文 / 0x5c 选项（"文本,FLAG"）
不收：0xfd 名札（0x2402 写入独立名字窗）、0xf5 引擎命令名（WINDOW_CHK 等）、0x3c/0x3d 音频、0x3b 图片
主角槽：1802=相崎（姓） / 0c02=恋（名）—— main(NSO) 内 UTF-8「名前は相崎恋」＋「苗字を変更します。」
"""
import sys, os, re, io

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gss_scr3 as G
import himehibi_lsdarc as L

ROMFS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "_work_himehibi", "romfs_base")
ROOT = "PRG_MAIN_0630"
EXTRA_TAIL = ["OMAKE_DRAMA"]
SLOT_NAME = {"1802": "相崎", "0c02": "恋"}

ents, _ = L.read_index(os.path.join(ROMFS, "SCRDATA.BIN"))
_data = open(os.path.join(ROMFS, "SCRDATA.ARC"), "rb").read()
SCRIPTS = {e["name"]: _data[e["off"]:e["off"] + e["usz"]] for e in ents}


def norm(n):
    n = n.strip().lower()
    return n[:-4] if n.endswith(".scr") else n


NAME2 = {norm(n): n for n in SCRIPTS}

RE_LINEBREAK = re.compile(r"\\n")
RE_CTRL = re.compile(r"\\[a-zA-Z]")
RE_AT = re.compile(r"@[a-zA-Z]")


def clean(s):
    s = RE_LINEBREAK.sub("", s)
    s = RE_CTRL.sub("", s)
    s = RE_AT.sub("", s)
    return s.strip().strip("\u3000").strip()


def subst(s, ops):
    srcs = []
    for t, v in ops[1:]:
        if t == 6:
            srcs.append(SLOT_NAME.get(v, ""))
        elif t == 3:
            srcs.append(v)
        elif t == 1 and v == "ffffffff":
            break
        else:
            srcs.append("")
    it = iter(srcs)
    return re.sub(r"%s", lambda m: next(it, ""), s)


def calls_of(name):
    res, err = G.disasm(SCRIPTS[name])
    out = []
    for off, op, size, ident, ops in res:
        if op in (0x1d, 0x1e):
            ss = [v for t, v in ops if isinstance(v, str)]
            if len(ss) >= 2:
                out.append(ss[0])
    return out


def crawl(root):
    order, seen = [], set()

    def rec(name):
        k = norm(name)
        if k in seen or k not in NAME2:
            return
        seen.add(k)
        order.append(NAME2[k])
        for c in calls_of(NAME2[k]):
            rec(c)

    rec(root)
    return order


def script_lines(name):
    res, err = G.disasm(SCRIPTS[name])
    for off, op, size, ident, ops in res:
        ss = [v for t, v in ops if t == 3]
        if op == 0x5a and ss:
            yield ("msg", clean(ss[0]))
        elif op == 0xfc and ss:
            yield ("msg", clean(subst(ss[0], ops)))
        elif op == 0xf0 and ss:
            yield ("title", clean(ss[0]))
        elif op == 0x5c:
            ss2 = [v for t, v in ops if t == 3]
            n = len(ss2)
            if ss2 and re.fullmatch(r"[0-9a-f]{8}", ss2[0]) and int(ss2[0], 16) == n - 1:
                ss2 = ss2[1:]
            for s in ss2:
                txt = s.rsplit(",", 1)[0] if "," in s else s
                yield ("choice", clean(txt))


if __name__ == "__main__":
    outfile = sys.argv[1] if len(sys.argv) > 1 else None
    order = crawl(ROOT)
    have = {norm(x) for x in order}
    for extra in EXTRA_TAIL:
        if extra in SCRIPTS and norm(extra) not in have:
            order.append(extra)
    lines, per = [], []
    for name in order:
        c = 0
        for kind, txt in script_lines(name):
            if txt:
                lines.append(txt)
                c += 1
        per.append((name, c))
    print(f"# {len(order)} scripts, {len(lines)} lines")
    print("# 0-line scripts:", sum(1 for _, c in per if c == 0))
    if outfile:
        with io.open(outfile, "w", encoding="utf-8-sig", newline="\n") as f:
            for l in lines:
                f.write(l + "\n")
        print("# wrote", outfile)
    else:
        for l in lines[:40]:
            print(l)
