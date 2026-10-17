#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""神さまと恋ゴコロ (NS-JP) text extract ---- Takuyo gss / LSDARC 'SCR 3.00'.

Chain: NSP(PFS0) -> program NCA (titlekey) -> RomFS -> SCRDATA.BIN/.ARC (LSDARC V.100)
       -> gss_codec (H/D/R) -> SCR 3.00 disasm -> lines.

Line rules (skill vn-custom-bytecode-text section 0):
  0x5a  message box text             -> one click = one line
  0xfc  message box text with %s     -> %s <- protagonist name slots
  0xf0  title card (扉文)            -> displayed
  0x5c  choices                      -> "text,FLAG" ; text = before last ASCII comma
  in-string: backslash-n = in-box line break (merge) ; backslash-c = control (drop)
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gss_lsdarc as L
import gss_scr3 as D

# protagonist default name (sjistext.csv ShiftJISBinary[1]=surname, [2]=given ; gss_emulate.cpp)
NAME_SLOTS = {"1802": "水無川", "0c02": "愛梨"}

# whole-line source-typo fixes (do NOT generalise into a regex)
TEXT_PATCH = {
    "（怒られる事も、失望される事も当然だと思ってた)":
        "（怒られる事も、失望される事も当然だと思ってた）",  # SORA_14: raw byte 0x29 ')'
}

# 0x5a strings starting with this are production notes (SE cues), skipped by the engine
COMMENT_PREFIX = "☆"

CALL_OPS = {0x1e, 0x1d, 0x102}
MSG_OPS = {0x5a, 0xfc}
TITLE_OP = 0xf0
OPT_OP = 0x5c

# system / UI / dev / gallery / voice / minigame -> excluded from the deliverable
EXCLUDE = set("""AUTOEXEC INIT SELECT SELECT2 RELOAD
PRG_ROUTE PRG_BG PRG_EFFECT PRG_EFFECTSTOP PRG_NAME PRG_PLATE PRG_STAND PRG_THREAD
YURASHI TIME_PASS CERO SUNDAY DEBUG 01GALLERY 01SYSTEM 02MINI_GAME 02SECRET_VOICE""".split())

# narrative extras appended after the main story
EXTRA_ORDER = ["03OMAKE", "CASE_1", "CASE_2", "CASE_3", "CASE_4", "CASE_5", "CASE_6", "04WEB"]

RE_NL = re.compile(r"\\n")
RE_CTRL = re.compile(r"\\[a-zA-Z]")


def clean(s):
    s = RE_NL.sub("", s)
    s = RE_CTRL.sub("", s)
    s = s.strip().strip("\u3000").strip()
    return TEXT_PATCH.get(s, s)


def subst(s, ops):
    it = iter([NAME_SLOTS.get(v, "") for t, v in ops[1:] if t == 6])
    return re.sub(r"%s", lambda m: next(it, ""), s)


def lines_of(name, scripts, stats):
    res, err = D.disasm(scripts[name])
    if err:
        raise RuntimeError("%s disasm error %r" % (name, err))
    for off, op, size, ident, ops in res:
        ss = [v for t, v in ops if t == 3]
        if op in MSG_OPS and ss:
            txt = clean(subst(ss[0], ops) if op == 0xfc else ss[0])
            if txt and not txt.startswith(COMMENT_PREFIX):
                stats[op] = stats.get(op, 0) + 1
                yield txt
        elif op == TITLE_OP and ss:
            txt = clean(ss[0])
            if txt:
                stats[op] = stats.get(op, 0) + 1
                yield txt
        elif op == OPT_OP:
            ss = [v for t, v in ops if t == 3]
            for s in ss:
                txt = clean(s.rsplit(",", 1)[0] if "," in s else s)
                if txt:
                    stats[op] = stats.get(op, 0) + 1
                    yield txt


def norm(name, names):
    n = name.strip()
    if n.lower().endswith(".scr"):
        n = n[:-4]
    return n


def build_order(scripts):
    lower = {k.lower(): k for k in scripts}

    def canon(n):
        n = norm(n, scripts)
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
    story = [n for n in order if n not in EXCLUDE]
    for e in EXTRA_ORDER:
        if e in scripts and e not in story:
            story.append(e)
    return story, seen, order


def main():
    romfs = sys.argv[1] if len(sys.argv) > 1 else "romfs"
    out = sys.argv[2] if len(sys.argv) > 2 else "神さまと恋ゴコロ_全文本.txt"
    scripts = L.unpack_all(os.path.join(romfs, "SCRDATA.BIN"), os.path.join(romfs, "SCRDATA.ARC"))
    order, seen, raw = build_order(scripts)
    stats = {}
    lines = []
    for name in order:
        lines.extend(lines_of(name, scripts, stats))
    with open(out, "w", encoding="utf-8-sig", newline="\n") as f:
        for l in lines:
            f.write(l + "\n")
    print("scripts: total=%d reached=%d in-order=%d" % (len(scripts), len(seen), len(order)))
    print("lines: total=%d  by-op=%s" % (len(lines), {hex(k): v for k, v in sorted(stats.items())}))
    print("wrote", out)


if __name__ == "__main__":
    main()
