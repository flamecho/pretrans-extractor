#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[NS-JP]SWEET CLOWN ~午前三時のオカシな道化師~ text extract (Takuyo gss / SCR 3.00).

Chain: XCI(packed hfs0) -> Program NCA (Standard crypto) -> RomFS
       SCRDATA.BIN/.ARC (LSDARC V.100, 386 entries, all isPacked=0) -> SCR 3.00 disasm
       + official patch v196608 (BKTR, applied over base via nstool --basenca).

Line rules:
  0x5a  message text                 -> one click = one line
  0xfc  message text with %s         -> %s <- protagonist name slots (1802 surname / 0c02 given)
  0xf0  title card (扉文)
  0x5c  choices                      -> "text ,FLAG" (text = before last ASCII comma)
  in-string: '\\c' = page clear (box cleared, waits for click) -> NEW line (one click)
             '\\n' = in-box soft wrap (no click)             -> merged into the same line
  0x5a "fixed default name" + 0xfc "%s variable name" are a MUTUALLY EXCLUSIVE branch pair
  (separated by 0x22/0x21/0x23 conditional ops) -> after slot substitution the two lines are
  byte-identical; keep one (structural dedupe, 371 pairs).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gss_lsdarc as L
import gss_scr3 as D

# sjistext.csv ShiftJISBinary[1]=橿野(姓) [2]=柘榴(名)  (gss_emulate.cpp default name table)
NAME_SLOTS = {"1802": "橿野", "0c02": "柘榴"}
# in-text macro (variable expansion at run time): GameLast = player-entered surname
TEXT_MACRO = {"@GameLast": "橿野"}

CALL_OPS = {0x1e, 0x1d, 0x102}
MSG_OPS = {0x5a, 0xfc}
TITLE_OP = 0xf0
OPT_OP = 0x5c

EXCLUDE = set("""AUTOEXEC INIT SELECT SELECT2 RELOAD
PRG_ROUTE PRG_BG PRG_EFFECT PRG_EFFECTSTOP PRG_NAME PRG_PLATE PRG_STAND PRG_THREAD
YURASHI TIME_PASS CERO DEBUG DEBUG2""".split())

# system UI: "skip the prologue you already read?" prompt + its yes/no buttons
SKIP_PROMPT = "≪プロローグをスキップしますか？≫"

RE_CTRL = re.compile(r"\\[a-zA-Z]")


def clean(s):
    s = s.replace("\\n", "")
    s = RE_CTRL.sub("", s)
    for k, v in TEXT_MACRO.items():
        s = s.replace(k, v)
    return s.strip().strip("\u3000").strip()


def subst(s, ops):
    it = iter([NAME_SLOTS.get(v, "") for t, v in ops[1:] if t == 6])
    return re.sub(r"%s", lambda m: next(it, ""), s)


def lines_of(name, scripts, stats):
    """yield (op, text) keeping the opcode so mutex branch pairs can be collapsed."""
    res, err = D.disasm(scripts[name])
    if err:
        raise RuntimeError("%s disasm error %r" % (name, err))
    for off, op, size, ident, ops in res:
        ss = [v for t, v in ops if t == 3]
        if op in MSG_OPS and ss:
            raw = subst(ss[0], ops) if op == 0xfc else ss[0]
            for seg in raw.split("\\c"):
                txt = clean(seg)
                if txt:
                    stats[op] = stats.get(op, 0) + 1
                    yield op, txt
        elif op == TITLE_OP and ss:
            for seg in ss[0].split("\\c"):
                txt = clean(seg)
                if txt:
                    stats[op] = stats.get(op, 0) + 1
                    yield op, txt
        elif op == OPT_OP:
            for s in ss:
                txt = clean(s.rsplit(",", 1)[0] if "," in s else s)
                if txt:
                    stats[op] = stats.get(op, 0) + 1
                    yield op, txt


def norm(name):
    n = name.strip()
    if n.lower().endswith(".scr"):
        n = n[:-4]
    return n


def build_order(scripts):
    lower = {k.lower(): k for k in scripts}

    def canon(n):
        n = norm(n)
        return lower.get(n.lower(), n)

    def calls(name):
        res, _ = D.disasm(scripts[name])
        out = []
        for off, op, size, ident, ops in res:
            if op in CALL_OPS:
                ss = [v for t, v in ops if t == 3]
                if len(ss) >= 2:
                    out.append(canon(ss[0]))
        return out

    order, seen = [], set()

    def rec(n):
        if n in seen or n not in scripts:
            return
        seen.add(n)
        order.append(n)
        for c in calls(n):
            rec(c)

    rec("AUTOEXEC")
    return [n for n in order if n not in EXCLUDE], seen, order


def main():
    romfs = sys.argv[1] if len(sys.argv) > 1 else "romfs"
    out = sys.argv[2] if len(sys.argv) > 2 else "sweetclown.txt"
    scripts = L.unpack_all(os.path.join(romfs, "SCRDATA.BIN"),
                           os.path.join(romfs, "SCRDATA.ARC"))
    order, seen, raw_order = build_order(scripts)
    stats = {}
    seq = []
    for name in order:
        seq.extend(lines_of(name, scripts, stats))

    # drop the system "skip prologue" prompt block (prompt + its はい/いいえ buttons)
    if any(t == SKIP_PROMPT for _, t in seq):
        i = next(i for i, (_, t) in enumerate(seq) if t == SKIP_PROMPT)
        del seq[i:i + 3]

    # structural dedupe: 0x5a(fixed default name) -> 0xfc(%s var name), identical after subst
    dedup = 0
    out_lines = []
    for op, txt in seq:
        if out_lines and out_lines[-1][1] == txt and (out_lines[-1][0], op) == (0x5a, 0xfc):
            dedup += 1
            continue
        out_lines.append((op, txt))

    with open(out, "w", encoding="utf-8-sig", newline="\n") as f:
        for _, l in out_lines:
            f.write(l + "\n")
    print("scripts: total=%d reached=%d in-order=%d" % (len(scripts), len(seen), len(order)))
    print("lines: total=%d (dedupe -%d)  by-op=%s"
          % (len(out_lines), dedup, {hex(k): v for k, v in sorted(stats.items())}))
    print("wrote", out)


if __name__ == "__main__":
    main()
