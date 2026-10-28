#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Panic Palette (NS-JP, TAKUYO) text extract.

Chain: NSP -> PFS0 -> program NCA (Titlekey crypto) -> RomFS
       -> SCRDATA.BIN/.ARC (LSDARC V.100, all isPacked=0) + SCR 2.00 disasm -> lines.

Line rules (skill vn-custom-bytecode-text section 0):
  0x5a  message box text              -> one click = one line
  0xfc  message box text with %s      -> %s <- name slots (surname / given)
  0xf0  chapter / scene title card    -> displayed
  0x5c  choices                       -> "0xNNNtext" or "text,FLAG"
  0x149 ending poem lines (EPI)       -> displayed one by one
  in-string: \\n = in-box line break (merge) ; \\c = control code (drop)
             @y/@w = wait/effect codes (drop)
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gss_lsdarc as L
import himehibi_disasm as D

# protagonist name slots: 1802 = surname 依藤, 0c02 = given 亜貴 (renameable)
NAME_SLOTS = {"1802": "依藤", "0c02": "亜貴"}

CALL_OPS = {0x1e, 0x1d, 0x102}
MSG_OPS = {0x5a, 0xfc}
TITLE_OP = 0xf0
OPT_OP = 0x5c
ED_OP = 0x149

# system / UI / debug -> excluded
EXCLUDE = set("""AUTOEXEC INIT INITFLG RELOAD PRG_BG PRG_DAY PRG_NAME PRG_PLACE PRG_STAND
PRG_FLG_CTRL SELECT2 YURASHI SYS_EYE_CATCH PRG_EFFECTSTOP DEBUG_SCR _CERO""".split())

# bonus reading content not reachable from the AUTOEXEC call graph (menu driven)
EXTRA_ORDER = ["KATUDOUNISSI%02d" % i for i in range(9)] + \
              ["SUBARASIKIHIBI%02d" % i for i in range(1, 15)]

SKIP_PROMPT = "このシナリオをスキップしますか？"
SKIP_OPTS = {"はい", "いいえ"}
ITEM_PROMPT = "何を手に入れますか？"

RE_NL = re.compile(r"\\n")
RE_CTRL = re.compile(r"\\[a-zA-Z]")
RE_OPT_PREFIX = re.compile(r"^0x[0-9A-Fa-f]+")
# in-string markup: $i0xNN = inline term/effect index code (never rendered, one per
# glossary-term occurrence: 「$i0x03烏羽一徒（からすばかずと）」 …) -> strip
RE_INDEX = re.compile(r"\$i0x[0-9A-Fa-f]{2}")


# 名札がテキスト窗口内に 1 行目として印字される形（名\n「台詞」）。
# 本エンジンは専用名札窗口（0xfd slot 2402 ＋ PRG_NAME.SCR）を持つので、これは名札行
# ⇒ 整行破棄（話者プレフィックスは付けない）。
NAME_LABELS = {"クリスティーヌ"}
RE_NAME_LABEL = re.compile(r"^([^\s「」（）\\]{1,12})\\n(?=「)")


def clean(s):
    m = RE_NAME_LABEL.match(s)
    if m and m.group(1) in NAME_LABELS:
        s = s[m.end():]
    s = RE_NL.sub("", s)
    s = RE_CTRL.sub("", s)
    s = RE_INDEX.sub("", s)
    s = s.replace("@y", "").replace("@w", "")
    return s.strip().strip("\u3000").strip()


def subst(s, ops):
    it = iter([NAME_SLOTS.get(v, "") for t, v in ops[1:] if t == 6])
    return re.sub(r"%s", lambda m: next(it, ""), s)


def opt_text(s):
    s = s.rsplit(",", 1)[0] if "," in s else s
    s = RE_OPT_PREFIX.sub("", s)
    return s.rstrip(" ")


def lines_of(name, scripts, stats):
    res, err = D.disasm(scripts[name])
    if err:
        raise RuntimeError("%s disasm error %r" % (name, err))
    drop_next_opts = False
    for off, op, size, ident, ops in res:
        ss = [v for t, v in ops if t == 3]
        if op in MSG_OPS and ss:
            raw = ss[0]
            if raw.strip() == SKIP_PROMPT or raw.strip() == "@y" + SKIP_PROMPT + "@w":
                drop_next_opts = True
                continue
            if name == "ITEM" and raw.replace("@y", "").replace("@w", "").strip() == ITEM_PROMPT:
                drop_next_opts = True
                continue
            txt = clean(subst(raw, ops) if op == 0xfc else raw)
            if txt:
                stats[op] = stats.get(op, 0) + 1
                yield txt
        elif op == TITLE_OP and ss:
            if "マップ選択中" in ss[0]:
                continue
            txt = clean(ss[0])
            if txt:
                stats[op] = stats.get(op, 0) + 1
                yield txt
        elif op == OPT_OP:
            if drop_next_opts:
                cand = {opt_text(s).strip() for s in ss}
                if cand <= SKIP_OPTS or len(cand) <= 3:
                    drop_next_opts = False
                    continue
                drop_next_opts = False
            for s in ss:
                txt = clean(opt_text(s))
                if txt:
                    stats[op] = stats.get(op, 0) + 1
                    yield txt
        elif op == ED_OP and ss:
            txt = clean(ss[0])
            if txt:
                stats[op] = stats.get(op, 0) + 1
                yield txt


def _canon(n, lower):
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
                    out.append(_canon(ss[0], lower))
        return out

    order, seen = [], set()

    def rec(n):
        if n in seen or n not in scripts:
            return
        seen.add(n)
        order.append(n)
        for c in calls(n):
            rec(c)

    # AUTOEXEC reaches only the system scripts; the story entry is launched by the
    # engine's "new game" menu => PRG_MAIN_0418 (no script calls it).
    rec("AUTOEXEC")
    rec("PRG_MAIN_0418")
    story = [n for n in order if n not in EXCLUDE]
    for e in EXTRA_ORDER:
        if e in scripts and e not in story:
            story.append(e)
    return story, seen, order


def main():
    romfs = sys.argv[1] if len(sys.argv) > 1 else "_work_panic/romfs"
    out = sys.argv[2] if len(sys.argv) > 2 else "提取结果/[NS-JP]Panic Palette ～パニック パレット～.txt"
    ents, arc = L.load(os.path.join(romfs, "SCRDATA.BIN"), os.path.join(romfs, "SCRDATA.ARC"))
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
