#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract all displayed text from ひめひび -Princess Days- (PSV, Takuyo gss / LSDARC 'SCR 2.00').

Text-bearing opcodes:
  0x5a  message box text           -> one click = one line
  0xfc  message box text with %s   -> substitution sources = following operands
  0xf0  scenario title card        -> displayed
  0x5c  choice options             -> "text,FLAG" (text before last ASCII comma)
Excluded: 0xfd (name box / graphics), 0x3c/0x3d (audio), 0x3b (image), 0x1d/0x1e (calls), ...
"""
import sys, os, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import himehibi_disasm as H

ents, SCRIPTS = H.load()
def norm(n):
    n = n.strip().lower()
    return n[:-4] if n.endswith(".scr") else n
NAME2 = {norm(n): n for n in SCRIPTS}

# protagonist name slots (set only in the debug menu; fixed default here)
SLOT_NAME = {"0c02": "恋", "1802": "相崎"}

RE_LINEBREAK = re.compile(r"\\n")
RE_CTRL = re.compile(r"\\[a-zA-Z]")   # \c and any other backslash code
RE_AT = re.compile(r"@[a-zA-Z]")

def clean(s):
    s = RE_LINEBREAK.sub("", s)
    s = RE_CTRL.sub("", s)
    s = RE_AT.sub("", s)
    s = s.strip().strip("\u3000").strip()
    return s

def subst(s, ops):
    """Substitute %s in a 0xfc string using the operands after the string."""
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
    b = SCRIPTS[name]
    res, err = H.disasm(b)
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
    """Yield (kind, text) for a script in instruction order."""
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
            ss = [v for t, v in ops if t == 3]
            # first operand may be a u32 option count (8 hex digits)
            n = len(ss)
            if ss and re.fullmatch(r"[0-9a-f]{8}", ss[0]) and int(ss[0], 16) == len(ss) - 1:
                ss = ss[1:]
            for s in ss:
                txt = s.rsplit(",", 1)[0] if "," in s else s
                yield ("choice", clean(txt))

if __name__ == "__main__":
    import io
    root = sys.argv[1] if len(sys.argv) > 1 else "PRG_MAIN_0630"
    outfile = sys.argv[2] if len(sys.argv) > 2 else None
    order = crawl(root)
    # bonus drama (menu-accessible) appended after the main story
    for extra in ["OMAKE_DRAMA"]:
        if extra in SCRIPTS and norm(extra) not in {norm(x) for x in order}:
            order.append(extra)
    lines = []
    per = []
    for name in order:
        c = 0
        for kind, txt in script_lines(name):
            if txt:
                lines.append(txt); c += 1
        per.append((name, c))
    print(f"# {len(order)} scripts, {len(lines)} lines")
    if outfile:
        with io.open(outfile, "w", encoding="utf-8-sig", newline="\n") as f:
            for l in lines:
                f.write(l + "\n")
        print("# wrote", outfile)
    else:
        for l in lines[:60]:
            print(l)
