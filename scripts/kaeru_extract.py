#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""カエル畑DEつかまえて☆彡 (NS-JP, TAKUYO) text extract.

Chain: XCI -> secure HFS0 -> program NCA (Standard crypto, gamecard) -> RomFS
       -> SCRDATA1.BIN/.ARC (LSDARC V.100, all isPacked=0) + SCR 2.00 disasm -> lines.

Line rules (skill vn-custom-bytecode-text section 0):
  0x5a  message box text              -> one click = one line
  0xfc  message box text with %s      -> %s <- name slots (surname/given/nick)
  0xf0  chapter title card (扉文)     -> displayed
  0x5c  choices                       -> "text ,FLAG" ; text = before last ASCII comma
  in-string: \\n = in-box line break (merge) ; \\c = control code (drop)
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gss_lsdarc as L
import himehibi_disasm as D

# protagonist name slots (default: 菅野 風羽 / nickname スガ ; renameable in-game)
NAME_SLOTS = {"1802": "菅野", "0c02": "風羽", "f405": "スガ"}

# ★ 2nd name-insertion form: 0xf0 (chapter/scene title card) carries ONLY a string operand,
#   so there is no slot operand to substitute. The author used a textual macro instead:
#   "@GameLast" == surname slot 1802. Seen 2x, both in 0xf0 titles:
#     COM013@0x10 'おはようございます、@GameLastです'   -> 菅野です (the line right below says 「菅野です」)
#     MATO003@0x10 '@GameLast愛護週間で優先です'        -> 菅野愛護週間 (same term used 5x in text)
NAME_MACROS = {"@GameLast": NAME_SLOTS["1802"]}
RE_NAME_MACRO = re.compile("|".join(re.escape(k) for k in NAME_MACROS))

# whole-line constant fixes for source inconsistencies (do NOT generalise into a regex).
# NOR020 @0xdc7: the yokai-glossary popup (妖怪図鑑 / 用語解説, shown after PRG_NAME.SCR NAME_NON)
# is the only one of the nine in-game glossary cards written WITHOUT the 【】 brackets
# (cf. COM001 【謎の小さいオッサン】, COM002 【ナナフシ】, HINO007_HIR 【トリコロール】 …).
# Restored to the game's own 【見出し語】：解説 convention.
TEXT_PATCH = {
    "烏天狗：なんか羽とか生えてて空が飛べる妖怪。羽は黒っぽい。":
        "【烏天狗】：なんか羽とか生えてて空が飛べる妖怪。羽は黒っぽい。",
}

CALL_OPS = {0x1e}
MSG_OPS = {0x5a, 0xfc}
TITLE_OP = 0xf0
OPT_OP = 0x5c

# system / UI / debug / mini-game -> excluded from the deliverable
EXCLUDE = set("""AUTOEXEC INIT PRG_BG PRG_EFFECT PRG_NAME PRG_PLATE PRG_ROUTE PRG_STAND
PRG_THREAD RELOAD SELECT2 MINI_HOU MINI_GOMI MINI_KINOKO""".split())

# bonus narrative content not reachable from the AUTOEXEC call graph
EXTRA_ORDER = ["KAKEAI_HAM01", "KAKEAI_HAM02", "KAKEAI_HIR01", "KAKEAI_HIR02",
               "KAKEAI_KUG01", "KAKEAI_KUG02", "KAKEAI_MAI01", "KAKEAI_MAI02",
               "KAKEAI_NIR02", "KAKEAI_NOR01", "KAKEAI_TOG01", "KAKEAI_TOG02",
               "SP_DORAMA01", "SP_DORAMA02", "SP_DORAMA03", "SP_DORAMA04",
               "SP_DORAMA05", "SP_DORAMA06", "SP_DORAMA07", "SP_DORAMA08",
               "SP_DORAMA09", "SP_DORAMA10"]

RE_NL = re.compile(r"\\n")
RE_CTRL = re.compile(r"\\[a-zA-Z]")


def clean(s):
    s = RE_NL.sub("", s)
    s = RE_CTRL.sub("", s)
    s = RE_NAME_MACRO.sub(lambda m: NAME_MACROS[m.group()], s)
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
            if txt:
                stats[op] = stats.get(op, 0) + 1
                yield txt
        elif op == TITLE_OP and ss:
            txt = clean(ss[0])
            if txt:
                stats[op] = stats.get(op, 0) + 1
                yield txt
        elif op == OPT_OP:
            for s in ss:
                txt = clean(s.rsplit(",", 1)[0] if "," in s else s)
                if txt:
                    stats[op] = stats.get(op, 0) + 1
                    yield txt


def _canon(n, scripts, lower):
    n = n.strip()
    if n.lower().endswith(".scr"):
        n = n[:-4]
    return lower.get(n.lower(), n)


def build_order(scripts):
    lower = {k.lower(): k for k in scripts}

    def calls(name):
        res, _ = D.disasm(scripts[name])
        out = []
        for off, op, size, ident, ops in res:
            if op in CALL_OPS:
                ss = [v for t, v in ops if t == 3]
                if ss:
                    out.append(_canon(ss[0], scripts, lower))
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
    # traverse excluded scripts too (they may call story), but drop them from output
    story = [n for n in order if n not in EXCLUDE]
    for e in EXTRA_ORDER:
        if e in scripts and e not in story:
            story.append(e)
    return story, seen, order


def main():
    romfs = sys.argv[1] if len(sys.argv) > 1 else "_work_kaeru/romfs"
    out = sys.argv[2] if len(sys.argv) > 2 else "提取结果/カエル畑DEつかまえて☆彡_全文本.txt"
    ents, arc = L.load(os.path.join(romfs, "SCRDATA1.BIN"), os.path.join(romfs, "SCRDATA1.ARC"))
    scripts = {e["name"]: L.unpack_entry(arc, e) for e in ents}
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
