#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""[NS-JP]死神と少女 (The Reaper And The Girl) text extract.

Chain:
  NSZ -> NSP (nsz -D) -> PFS0 -> Program NCA (titlekey, nstool --tik) -> RomFS
    romfs/1/SCRDATA.BIN/.ARC = LSDARC V.100, 461 x "SCR 3.00" (unpacked, isPacked=0)
    romfs/0/main (NSO)      = コトノハ（用語）辞典表（UTF-8 文字列 + u32 指针表 @0x8205c）

Order: PRG_ROUTE.SCR 的 0x1e <file> <label> 线性派发序（443 唯一目标）。
Extras: 絵本 EHON01/02/04/05（絵本菜单派发，脚本内无静态引用）。

Line rules (单版式):
  0x5a  message text        -> one click = one box = one line; 框内 `\n` = 排版换行，删换行拼接
  0xfc  message text with %s -> %s <- slot 0c02 (given name 紗夜)
  0x149 picture-book narration (絵本 text op) -> one click = one box = one line
  0x5c  choices             -> "text,FLAG" (text = before last ASCII comma)
  0xf0  scene id card 【一章-27】 -> NOT collected (CHAPTER screen's scene label, UI)
  inline markup stripped: '#...#(STAND sprite)', '@z/@0', '$...$', trailing '\d' / '\u'
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gss_lsdarc as L
import gss_scr3 as D

ROMFS = "_work_shini/romfs"
ROOT = ROMFS + "/1"
MAIN_NSO = ROMFS + "/0/main"
OUT = "提取结果/[NS-JP]死神と少女.txt"

NAME = "紗夜"          # slot 0c02 default (PRG_NAME / INIT 0x108 / PRG_ROUTE 0x108)

MSG_OPS = {0x5A, 0xFC, 0x149}
OPT_OP = 0x5C
SCENE_OP = 0xF0

# 系统 / UI / 演出 / 调试 —— 不参与正文
EXCLUDE = set("""AUTOEXEC INIT INITFLG DEBUG RELOAD YURASHI SELECT2
PRG_BG PRG_EFFECT PRG_NAME PRG_PLATE PRG_ROUTE PRG_STAND PRG_THREAD PRG_TEXT""".split())

# 絵本／物語（絵本菜单派发，脚本内无静态 0x1e 引用）；顺序取用語表「物語」段顺序。
# EHON01「籠の鳥」全 31 行中 30 行与 OP-02 逐字相同（同一故事在序章已完整上屏）⇒ 不重复收录。
EHON = ["SHINIGAMI_PIC", "EHON05", "EHON02", "EHON04"]

RE_TAG = re.compile(r"#[^#]{0,80}#")     # #STAND\XXXX.bmp 3#
RE_AT = re.compile(r"@[zZ0]")
RE_NL = re.compile(r"\\n[\u3000 ]*")
RE_TAIL = re.compile(r"(?:\\d|\\u)+$")


def clean(s):
    s = RE_TAG.sub("", s)          # inline sprite/expression tag
    s = RE_AT.sub("", s)           # @z ... @0  display-chunk markers
    s = s.replace("$", "")         # emphasis delimiters (keep inner text)
    s = RE_TAIL.sub("", s)         # end-of-box wait codes
    s = s.replace("%s", NAME)
    return s.strip().strip("\u3000").strip()


def segments(s):
    """框内 `\\n` ＝排版换行：逐段清理后删换行拼接，得到「一次点击＝一行」的整行文本。

    （4,324 处 `\\n` 里 3,372 处前段为空 ＝ `\\n\\n\\n` 连打的框内空行定位，
    其余 952 处也是排版换行，非语义断行 ⇒ 一律合并进同一行。）
    """
    parts = [clean(x) for x in s.split("\\n")]
    return "".join(p for p in parts if p)


def subst_ops(ops):
    return [v for t, v in ops if t == 6]


def lines_of(name, scripts, stats, seen):
    res, err = D.disasm(scripts[name])
    if err:
        raise RuntimeError("%s disasm error %r" % (name, err))
    prev = None          # (idx, text) of last emitted message box
    for k, (off, op, size, ident, ops) in enumerate(res):
        ss = [v for t, v in ops if t == 3]
        if op in MSG_OPS and ss:
            txt = segments(ss[0])
            if not txt:
                continue
            # 互斥分支（if 0x21 / else 0x23 夹在中间）里的同一句 = 同一点击的多版本：
            # 两版逐字相同 ⇒ 取一；无分支码夹着的同文重复（「どうして」×2 等）是真两句，保留。
            if prev and prev[1] == txt and any(res[j][1] in (0x21, 0x23) for j in range(prev[0] + 1, k)):
                stats["branchdup"] = stats.get("branchdup", 0) + 1
                prev = (k, txt)
                continue
            stats[op] = stats.get(op, 0) + 1
            seen.append(txt)
            prev = (k, txt)
        elif op == OPT_OP:
            for s in ss:
                txt = clean(s.rsplit(",", 1)[0] if "," in s else s)
                if not txt:
                    continue
                if txt.startswith("【分岐"):     # 开发用分支跳转菜单
                    stats["debugopt"] = stats.get("debugopt", 0) + 1
                    continue
                stats[op] = stats.get(op, 0) + 1
                seen.append(txt)


def canon(n, low):
    n = n.strip()
    if n.lower().endswith(".scr"):
        n = n[:-4]
    return low.get(n.lower(), n)


def dispatch_order(scripts):
    low = {k.lower(): k for k in scripts}
    res, _ = D.disasm(scripts["PRG_ROUTE"])
    order, seen = [], set()
    for off, op, size, ident, ops in res:
        if op != 0x1E:
            continue
        ss = [v for t, v in ops if t == 3]
        if len(ss) < 2:
            continue
        n = canon(ss[0], low)
        if n in seen:
            continue
        seen.add(n)
        order.append(n)
    return order


# ---------------------------------------------------------------- コトノハ辞典
def glossary():
    """0x8205c..0x82500: 99 x 12B records {u32 word, u32 desc, u32 desc2(0=none)}."""
    b = open(MAIN_NSO, "rb").read()
    b = _nso_text(b) or b
    start, end = 0x8205C, 0x82500

    def s(o):
        e = b.find(b"\x00", o)
        return b[o:e].decode("utf-8", "replace")

    out, i = [], start
    while i + 12 <= end:
        w, d1, d2 = struct.unpack_from("<III", b, i)
        if not (0x60000 < w < 0x80000):
            break
        out.append((s(w), s(d1)))
        if 0x60000 < d2 < 0x80000:
            out.append((s(w), s(d2)))
        i += 12
    return out


def _nso_text(b):
    """解 NSO（LZ4）后返回平铺镜像；已是平铺则返回 None."""
    if b[:4] != b"NSO0":
        return b
    import subprocess
    tmp = os.path.join(os.path.dirname(MAIN_NSO), "_main_flat.bin")
    if not os.path.exists(tmp):
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "nso_x.py"),
                        MAIN_NSO, tmp], check=True)
    return open(tmp, "rb").read()


def main():
    scripts = L.unpack_all(os.path.join(ROOT, "SCRDATA.BIN"), os.path.join(ROOT, "SCRDATA.ARC"))

    order = dispatch_order(scripts)
    stats, lines = {}, []

    for name in order:
        if name in EXCLUDE:
            continue
        if name in scripts:
            lines_of(name, scripts, stats, lines)
    for name in EHON:
        if name in scripts:
            lines_of(name, scripts, stats, lines)

    gloss = glossary()
    for word, desc in gloss:
        w = word.replace("%s", NAME).strip()
        d = desc.replace("%s", NAME).strip()
        if w and d:
            stats["gloss"] = stats.get("gloss", 0) + 1
            lines.append("【%s】%s" % (w, d))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    print("scripts dispatched=%d  used=%d" % (len(order), len([n for n in order if n in scripts and n not in EXCLUDE])))
    print("lines=%d  by-op=%s" % (len(lines), {hex(k): v for k, v in stats.items() if isinstance(k, int)}))
    print("glossary=%d" % len(gloss))


if __name__ == "__main__":
    if len(sys.argv) > 1:                       # 备用路径（重跑时 romfs 位置可变）
        ROOT = sys.argv[1]
    if len(sys.argv) > 2:
        MAIN_NSO = sys.argv[2]
    main()
