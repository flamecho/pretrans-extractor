#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ひめひび ─New Princess Days!!─ 続！二学期 (NS-JP 01009B4012FC6000) 全文本提取。

引擎＝Takuyo gss 的 Switch 变体：
  romfs/SCRDATA.BIN  = LSDARC V.100 索引 (u32 count + count×{u32 isPacked,u32 off,u32 usize,u32 size,name\\0})
  romfs/SCRDATA.ARC  = 数据；本作 684/684 isPacked=0，脚本头 "SCR 3.00"
  SCR 3.00 指令：u16 op | u16 size(总长含 6B 头) | u16 id | operand*<u8 type><data>
                type 0x00→1B 0x01→4B 0x02→2B 0x03→NUL 结尾 CP932 0x04→2B 0x05→4B 0x06→2B
文本 op：0x5a 正文 / 0xfc 带 %s 正文（源＝后随 type6 槽）/ 0xf0 扉文 / 0x5c 选项（"文本,FLAG"）
名札：0xfd(2402) 写入独立名字窗 ⇒ 不收（本提取根本不取 0xfd）
主角槽：1802=上河（姓） / 0c02=菜々美（名）  —— main(NSO) 内含默认名 UTF-8 串 +「苗字を変更します/名前を変更します」
用法: python scripts/himehibi2ns_extract.py [outfile]
"""
import sys, os, re, io, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import himehibi_lsdarc as L
import gss_scr3 as G

ROMFS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "_work_himehibi2", "romfs")
ROOT = "PRG_MAIN_09_01"
EXTRA_TAIL = ["DRAMA00", "DRAMA01", "DRAMA02", "DRAMA03"]
SLOT_NAME = {"1802": "上河", "0c02": "菜々美"}
# 原文缺陷（源字节物理上缺 1 个全角右括号，絵文字「（；ー；」未闭合）⇒ 补回闭合符，报告登记
TEXT_PATCH = {
    "『連絡遅くてごめん＞＜　委員会長引いてまだかかるかもだから、先に帰ってもいいよ……（；ー；』":
    "『連絡遅くてごめん＞＜　委員会長引いてまだかかるかもだから、先に帰ってもいいよ……（；ー；）』",
}

ents, _ = L.read_index(os.path.join(ROMFS, "SCRDATA.BIN"))
_d = open(os.path.join(ROMFS, "SCRDATA.ARC"), "rb").read()
SCRIPTS = {e["name"]: _d[e["off"]:e["off"] + e["usz"]] for e in ents}


def norm(n):
    n = n.strip().lower()
    return n[:-4] if n.endswith(".scr") else n


NAME2 = {norm(n): n for n in SCRIPTS}

RE_LINEBREAK = re.compile(r"\\n")
RE_CTRL = re.compile(r"\\[a-zA-Z]")
RE_AT = re.compile(r"@[a-zA-Z0-9]+")


def clean(s):
    s = RE_LINEBREAK.sub("", s)
    s = RE_CTRL.sub("", s)
    s = RE_AT.sub("", s)
    s = s.strip().strip("\u3000").strip()
    return TEXT_PATCH.get(s, s)


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


def _pat_to_rx(pat):
    out, i = [], 0
    while i < len(pat):
        if pat[i] == "%":
            j = i + 1
            if j < len(pat) and pat[j] == "0":
                j += 1
            while j < len(pat) and pat[j].isdigit():
                j += 1
            if j < len(pat) and pat[j] in "ds":
                out.append(r"\d+" if pat[j] == "d" else r"\w+")
                i = j + 1
                continue
        out.append(re.escape(pat[i]))
        i += 1
    return "^" + "".join(out) + "$"


def expand_dyn(pat):
    """0x10c 的 printf 型脚本名（如 09_09_12_MAP_%d.scr）展开成实存脚本名。"""
    if "%" not in pat or not pat.lower().endswith(".scr"):
        return []
    rx = _pat_to_rx(pat[:-4])
    out = [n for n in SCRIPTS if re.match(rx, n)]
    return sorted(out, key=lambda x: [int(t) if t.isdigit() else t.lower()
                                      for t in re.split(r"(\d+)", x)])


def calls_of(name):
    res, _ = G.disasm(SCRIPTS[name])
    out = []
    for off, op, size, ident, ops in res:
        ss = [v for t, v in ops if t == 3]
        if op in (0x1d, 0x1e) and len(ss) >= 2:
            out.append(ss[0])
        elif op == 0x10c:
            for s in ss:
                out.extend(expand_dyn(s))
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
    res, _ = G.disasm(SCRIPTS[name])
    # 槽字符串表：0xfd 赋值 / 0x107 追加（= 引擎的字符串拼接）/ 0x106 清空
    slots = dict(SLOT_NAME)  # 主角姓/名槽的默认值（可改名，引擎会在 INITFLG 里注入）
    for off, op, size, ident, ops in res:
        ss = [v for t, v in ops if t == 3]
        if op == 0xfd and len(ops) >= 2 and ops[0][0] == 6:
            dst, src = ops[0][1], ops[1]
            slots[dst] = src[1] if src[0] == 3 else slots.get(src[1], "") if src[0] == 6 else ""
        elif op == 0x107 and len(ops) >= 2 and ops[0][0] == 6:
            dst, src = ops[0][1], ops[1]
            add = src[1] if src[0] == 3 else slots.get(src[1], "") if src[0] == 6 else ""
            slots[dst] = slots.get(dst, "") + add
        elif op == 0x106 and ops and ops[0][0] == 6:
            slots.pop(ops[0][1], None)
        if op == 0x5a and ss:
            yield ("msg", clean(ss[0]))
        elif op == 0xfc and ss:
            yield ("msg", clean(subst(ss[0], ops)))
        elif op == 0xf0:
            if ss:
                yield ("title", clean(ss[0]))
            elif ops and ops[0][0] == 6:
                yield ("title", clean(slots.get(ops[0][1], "")))
        elif op == 0x5c:
            for s in ss:
                txt = s.rsplit(",", 1)[0] if "," in s else s
                yield ("choice", clean(txt))


if __name__ == "__main__":
    outfile = sys.argv[1] if len(sys.argv) > 1 else None
    order = crawl(ROOT)
    have = {norm(x) for x in order}
    for extra in EXTRA_TAIL:
        if extra in SCRIPTS and norm(extra) not in have:
            order.append(extra)
            have.add(norm(extra))
    lines, per, kinds = [], [], collections.Counter()
    for name in order:
        c = 0
        for kind, txt in script_lines(name):
            if txt:
                lines.append(txt)
                kinds[kind] += 1
                c += 1
        per.append((name, c))
    sys.stderr.write("# %d scripts, %d lines %s\n" % (len(order), len(lines), dict(kinds)))
    for name, c in per:
        if c:
            sys.stderr.write("#   %s: %d\n" % (name, c))
    if outfile:
        with io.open(outfile, "w", encoding="utf-8-sig", newline="\n") as f:
            for l in lines:
                f.write(l + "\n")
        sys.stderr.write("# wrote " + outfile + "\n")
    else:
        for l in lines[:60]:
            print(l)
