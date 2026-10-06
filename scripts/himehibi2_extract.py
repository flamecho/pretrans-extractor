#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract all displayed text from ひめひび ─New Princess Days!!─ 続！二学期
(PSV PCSG01144, Takuyo gss / LSDARC 'SCR 2.00').

Text-bearing opcodes:
  0x5a  message box text            -> one click = one line
  0xfc  message box text with %s    -> substitution sources = following slot operands
  0xf0  scenario title card         -> displayed
  0x5c  choice options              -> "text,FLAG" (text before last ASCII comma)
Control ops:
  0x1e / 0x1d  direct script call (file,label) -> crawl order
  0x10c        dynamic script call by printf name ("09_09_12_MAP_%d.scr") -> expand
Excluded: 0xfd (name box / graphics), 0x3c/0x3d (audio), 0x3b (image), ...
"""
import sys, os, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import himehibi_disasm as H

ROOT = "PRG_MAIN_09_01"
EXTRA_TAIL = ["DRAMA00", "DRAMA01", "DRAMA02", "DRAMA03"]
# protagonist slots: 0x7002 = surname, 0x6402 = given name (game default 上河/菜々美)
SLOT_NAME = {"7002": "上河", "6402": "菜々美"}

ents, SCRIPTS = H.load()


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


def _pat_to_rx(pat):
    out = []
    i = 0
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
    """expand a printf-style .scr pattern to existing script names, sorted."""
    if not pat.lower().endswith(".scr") or "%" not in pat:
        return []
    rx = _pat_to_rx(pat[:-4])  # LSDARC entry names carry no extension
    out = []
    for nm in SCRIPTS:
        if re.match(rx, nm):
            out.append(nm)
    # natural numeric order
    def key(x):
        return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", x)]
    return sorted(out, key=key)


def calls_of(name):
    b = SCRIPTS[name]
    res, err = H.disasm(b)
    out = []
    for off, op, size, ident, ops in res:
        if op in (0x1d, 0x1e):
            ss = [v for t, v in ops if isinstance(v, str)]
            if len(ss) >= 2:
                out.append(ss[0])
        elif op == 0x10c:
            ss = [v for t, v in ops if isinstance(v, str)]
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
    b = SCRIPTS[name]
    res, err = H.disasm(b)
    for off, op, size, ident, ops in res:
        ss = [v for t, v in ops if t == 3]
        if op == 0x5a and ss:
            yield ("msg", clean(ss[0]))
        elif op == 0xfc and ss:
            yield ("msg", clean(subst(ss[0], ops)))
        elif op == 0xf0 and ss:
            yield ("title", clean(ss[0]))
        elif op == 0x5c:
            for s in ss:
                txt = s.rsplit(",", 1)[0] if "," in s else s
                yield ("choice", clean(txt))


if __name__ == "__main__":
    import io
    root = sys.argv[1] if len(sys.argv) > 1 else ROOT
    outfile = sys.argv[2] if len(sys.argv) > 2 else None
    order = crawl(root)
    have = {norm(x) for x in order}
    for extra in EXTRA_TAIL:
        if extra in SCRIPTS and norm(extra) not in have:
            order.append(extra)
            have.add(norm(extra))
    lines = []
    per = []
    for name in order:
        c = 0
        for kind, txt in script_lines(name):
            if txt:
                lines.append(txt)
                c += 1
        per.append((name, c))
    sys.stderr.write(f"# {len(order)} scripts, {len(lines)} lines\n")
    for name, c in per:
        if c:
            sys.stderr.write(f"#   {name}: {c}\n")
    if outfile:
        with io.open(outfile, "w", encoding="utf-8-sig", newline="\n") as f:
            for l in lines:
                f.write(l + "\n")
        sys.stderr.write("# wrote " + outfile + "\n")
    else:
        for l in lines[:80]:
            print(l)
