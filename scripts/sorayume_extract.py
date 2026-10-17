#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ソラ*ユメ (NS-JP, TAKUYO, TitleID 0100e6a027760000) text extract.

Chain: XCI -> secure HFS0 -> Program NCA (Standard crypto) -> RomFS
       -> SCRDATA.BIN/.ARC (LSDARC V.100, all isPacked=0) + SCR 2.00 disasm -> lines.

Same engine family as ひめひび (PSV) / Cafe Cuillere (PSV) / カエル畑DEつかまえて☆彡 (NS):
LSDARC V.100 index + SCR 2.00 instruction stream (u16 op | u8 size | u16 id | operands).

Line rules (skill vn-custom-bytecode-text section 0):
  0x5a  message box text              -> one click = one line
  0xfc  message box text with %s      -> %s <- following type-6 slot operands (1802/0c02/7c04)
  0xf0  title card (扉文)             -> displayed
  0x5c  choices                       -> "text,FLAG" (text before last ASCII comma);
                                         or (6,slot) form resolved from earlier 0xfd assignments
  in-string: \\n = in-box line break (merge) ; \\c = control code (drop)
             @r / @0 / @uXXXXXX / @y = style/colour/wait codes (drop)
             @GameFirst = surname macro (0xf0 title cards only)

Excluded: system/UI scripts; and 0x5c blocks guarded by the debug flag c808==1
(the engine's debug flag -- initialised to 0 in INIT.SCR and never set to 1 by any
shipped script, so those blocks are the developer flag-set menus: 好感度/ルート/フラグ設定).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import himehibi_disasm as D

SCR_DIR = "_work_sorayume/scr"
OMAKEDIR = "_work_sorayume/romfs/omake"

# protagonist 守永 皐月 (official site: 骨董屋の一人娘『守永皐月』) -- renameable.
NAME_SLOTS = {"1802": "守永", "0c02": "皐月", "7c04": "さっ"}
# 2nd insertion form: 0xf0 title card carries only a string, so the author used a text macro.
NAME_MACROS = {"@GameFirst": "守永"}

CHOICE_SLOTS = ("2006", "4806", "7006", "9806", "c006")

# Whole-line constant fixes for source bracket typos (do NOT generalise into a regex).
# 3x mixed 「/』 and 『/」 closings; 2x full-width （ closed with an ASCII ).
TEXT_PATCH = {
    "「お、お母さん……？\u3000今度はどうしたの？』": "「お、お母さん……？\u3000今度はどうしたの？」",
    "『そうそう！\u3000そういえば面白い話！\u3000ピラミッド見学してたんだけどね？」":
        "『そうそう！\u3000そういえば面白い話！\u3000ピラミッド見学してたんだけどね？』",
    "『あはは。……いいんだよ、さっちゃん小さかったしね」":
        "『あはは。……いいんだよ、さっちゃん小さかったしね』",
    "（……暇だな。どうしよう)": "（……暇だな。どうしよう）",
    "（今からでも戻って、調べてみようかな。……天文部)":
        "（今からでも戻って、調べてみようかな。……天文部）",
    # YAMA036 @0x4c9: source string ends '...感じる？' + NUL, closing 」 never written.
    "「……ここで最後だね。……何か感じる？": "「……ここで最後だね。……何か感じる？」",
}

MSG_OPS = {0x5a, 0xfc}
TITLE_OP = 0xF0
OPT_OP = 0x5C
CALL_OPS = {0x1E}

EXCLUDE = set("""AUTOEXEC INIT PRG_BG PRG_EFFECT PRG_NAME PRG_PLATE PRG_ROUTE PRG_STAND
RELOAD SELECT2""".split())

RE_NL = re.compile(r"\\n")
RE_CTRL = re.compile(r"\\[a-zA-Z]")
RE_AT = re.compile(r"@[A-Za-z0-9]+")


def clean(s):
    for k, v in NAME_MACROS.items():
        s = s.replace(k, v)
    s = RE_NL.sub("", s)
    s = RE_CTRL.sub("", s)
    s = RE_AT.sub("", s)
    s = s.strip().strip("\u3000").strip()
    return TEXT_PATCH.get(s, s)


def subst(s, ops):
    it = iter([NAME_SLOTS.get(v, "") for t, v in ops[1:] if t == 6])
    return re.sub(r"%s", lambda m: next(it, ""), s)


def debug_blocks(res):
    """Offsets of [0x22, matching 0x23] if-blocks whose condition is exactly `c808 == 1`."""
    blocks = []
    offs = [o for o, _, _, _, _ in res]
    for j, (off, op, size, ident, ops) in enumerate(res):
        if op != 0x0022:
            continue
        guard = False
        for k in (j - 1, j - 2):
            if k < 0:
                break
            if res[k][1] == 0x0036 and any(v == "c808" for t, v in res[k][4]) \
                    and any(v == "01000000" for t, v in res[k][4]):
                guard = True
                break
        if not guard:
            continue
        tgt = [v for t, v in ops if t == 4]
        if not tgt:
            continue
        for k in range(j + 1, len(res)):
            if res[k][1] == 0x0023 and any(v == tgt[0] for t, v in res[k][4]):
                blocks.append((off, offs[k]))
                break
    return blocks


def lines_of(name, scripts, stats):
    res, err = D.disasm(scripts[name])
    if err:
        raise RuntimeError("%s disasm error %r" % (name, err))
    dbg = debug_blocks(res)
    slotmap = {}
    for idx, (off, op, size, ident, ops) in enumerate(res):
        ss = [v for t, v in ops if t == 3]
        if op == 0x00FD and len(ss) == 1:
            for t, v in ops:
                if t == 6:
                    slotmap[v] = ss[0]
        elif op in MSG_OPS and ss:
            txt = clean(subst(ss[0], ops) if op == 0xFC else ss[0])
            if txt:
                stats[op] = stats.get(op, 0) + 1
                yield txt
        elif op == TITLE_OP and ss:
            txt = clean(ss[0])
            if txt:
                stats[op] = stats.get(op, 0) + 1
                yield txt
        elif op == OPT_OP:
            if any(a < off < b for a, b in dbg):
                stats["dbg"] = stats.get("dbg", 0) + 1
                continue
            out = []
            for t, v in ops:
                if t == 3:
                    s = v.rsplit(",", 1)[0] if "," in v else v
                    out.append(clean(s))
                elif t == 6 and v in CHOICE_SLOTS and v in slotmap:
                    s = slotmap[v].rsplit(":", 1)[0] if ":" in slotmap[v] else slotmap[v]
                    out.append(clean(s))
            for txt in out:
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

    rec("AUTOEXEC")
    return [n for n in order if n not in EXCLUDE], seen, order


def omake_lines(stats):
    """romfs/omake/NNst.dat = plain-text short stories shown by the engine's おまけ viewer.
    CRLF; consecutive non-empty lines are one wrapped display paragraph (merge them),
    blank lines separate paragraphs.  '@' = given name, '*' = surname
    (verified against main-story usage: '*さん' = 守永さん, '*悠月', '*@は今日も元気に')."""
    out = []
    for fn in sorted(os.listdir(OMAKEDIR)):
        t = open(os.path.join(OMAKEDIR, fn), "rb").read().decode("cp932")
        buf = []
        for line in t.split("\r\n") + [""]:
            if line.strip():
                buf.append(line.strip().strip("\u3000"))
                continue
            if buf:
                p = "".join(buf).replace("*", NAME_SLOTS["1802"]).replace("@", NAME_SLOTS["0c02"])
                p = p.strip().strip("\u3000").strip()
                if p:
                    out.append(TEXT_PATCH.get(p, p))
                    stats["omake"] = stats.get("omake", 0) + 1
                buf = []
    return out


def main():
    outpath = sys.argv[1] if len(sys.argv) > 1 else "提取结果/[NS-JP]ソラユメ_全文本.txt"
    scripts = {f[:-4]: open(os.path.join(SCR_DIR, f), "rb").read()
               for f in os.listdir(SCR_DIR)}
    order, seen, raw = build_order(scripts)
    stats = {}
    lines = []
    for name in order:
        lines.extend(lines_of(name, scripts, stats))
    lines.extend(omake_lines(stats))
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    with open(outpath, "w", encoding="utf-8-sig", newline="\n") as f:
        for l in lines:
            f.write(l + "\n")
    print("scripts total=%d reached=%d story=%d" % (len(scripts), len(seen), len(order)))
    print("lines=%d  stats=%s" % (len(lines),
          {(hex(k) if isinstance(k, int) else k): v for k, v in sorted(stats.items(), key=str)}))
    print("wrote", outpath)


if __name__ == "__main__":
    main()
