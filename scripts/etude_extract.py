#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract all displayed text from étude prologue 〜揺れ動く心のかたち〜 Portable
(PSP, ULJM-05252, Takuyo ｇss engine: LSDARC V.100 + 'SCR 2.00').

Same family as ひめひび -Princess Days- / Cafe Cuillere (see scripts/himehibi_*.py).

Container : PSP_GAME/USRDIR/SCRDATA.BIN  (LSDARC V.100 index, 683 scripts, all isPacked=0)
            PSP_GAME/USRDIR/SCRDATA.ARC  (payload)
EBOOT     : PSP_GAME/SYSDIR/BOOT.BIN is a PLAIN ELF ( = decrypted EBOOT.BIN ), and holds the
            engine's map-event script table (507 NUL-padded CP932 names, 4-byte aligned,
            starting at 0x6edf8 right after the 'GET_SCRIPT_NAME' native-function name).

Text-bearing opcodes (identical semantics to ひめひび/Cafe Cuillere):
  0x5a  message box text          -> one click = one line
  0x5c  choices                   -> (u32 count, "text,FLAG", ...) ; text = before last ASCII ','
Excluded: 0xfd (slot assign: 0c02 = name plate, 5003 = background image, ...),
          0x3c/0x3d (SE/BGM), 0x3b/0x107/0x10c/0x146 (images/format paths),
          0x1d/0x1e (script calls), 0x25/0x22/0x21/0x23/0x36/... (variables/flags/flow)
No %s / no ruby / no rename macro: the two protagonists (郡司　達也 / 佐伯　瞳) are
fixed, established characters -> names are written literally in the scripts.
"""
import sys, os, re, io

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
from himehibi_lsdarc import read_index
from himehibi_disasm import disasm

# extracted PSP_GAME tree (see the extract command in the report); default = ../_work_etude/iso
GAMEDIR = os.environ.get("ETUDE_DIR", os.path.join(HERE, "..", "_work_etude", "iso", "PSP_GAME"))
ISO = os.path.join(GAMEDIR, "USRDIR")
BOOT = os.path.join(GAMEDIR, "SYSDIR", "BOOT.BIN")
BOOT_TABLE_OFF = 0x6EDF8
NAME_RE = re.compile(r"^[A-Za-z0-9_\u3000-\u30ff\u4e00-\u9fff]{1,40}$")

# ---------------------------------------------------------------- system / debug
# Never contain displayed story text (verified: 0 x 0x5a apart from debug strings).
# NOTE: PRG_MESS is intentionally NOT excluded -- its 18 x 0x5a are the protagonist's
# on-screen map-command monologue (「アルバイト行こう」/「さて、帰るか」 …).
EXCLUDE = {
    "AUTOEXEC", "INIT", "INITFLG", "MAIN",
    "PRG_BG", "PRG_DEBUG_NOMAL", "PRG_DEBUG_VOICE", "PRG_DEBUG_GRAPH",
    "PRG_MAP", "PRG_OPENING", "PRG_ENDING", "PRG_NAME", "PRG_STAND",
    "PRG_DATE", "RELOAD", "YURASHI", "RUNBLE", "SELECT", "SELECT2",
}

RE_LINEBREAK = re.compile(r"\\n")          # in-box line break  -> merge
RE_CTRL = re.compile(r"\\[a-zA-Z]")        # \c (break) / \u (wait for input) -> drop
RE_AT = re.compile(r"@[a-zA-Z]")           # @y / @w (wait codes)            -> drop
RE_HASH = re.compile(r"#[A-Za-z0-9]+#")    # #w0# (wait)                     -> drop

# Half-width kana punctuation found in the source is normalised to the full-width form the
# rest of the corpus uses (evidence: 「そ、そう…」 full-width x116  vs  「そ､そうね」 half-width x1).
PUNCT_FIX = {"\uFF64": "\u3001"}           # ､ -> 、

# Whole-line fixes for genuine authoring typos in the source scripts (never blanket-regexed).
# Each key must occur exactly once, otherwise the extractor aborts.
TEXT_PATCH = {
    # M_SAN_TAT_10 : full-width （ ... half-width )  -> full-width ）
    "\uff08\u2026\u2026\u771f\u7530\u541b\uff1f\u3000\u3069\u3046\u3057\u305f\u3093\u3060\u308d\u3046\u2026\u2026)":
        "\uff08\u2026\u2026\u771f\u7530\u541b\uff1f\u3000\u3069\u3046\u3057\u305f\u3093\u3060\u308d\u3046\u2026\u2026\uff09",
    # S_SIN_02_A : （ ... half-width ) + stray 」  -> full-width ） (monologue convention)
    "\uff08\u2026\u2026\u3042\u3001\u30af\u30ec\u30fc\u30f3\u30b2\u30fc\u30e0\u3001\u65b0\u3057\u3044\u306e\u5165\u3063\u305f\u3093\u3060)\u300d":
        "\uff08\u2026\u2026\u3042\u3001\u30af\u30ec\u30fc\u30f3\u30b2\u30fc\u30e0\u3001\u65b0\u3057\u3044\u306e\u5165\u3063\u305f\u3093\u3060\uff09",
}


def clean(s):
    s = RE_LINEBREAK.sub("", s)
    s = RE_CTRL.sub("", s)
    s = RE_AT.sub("", s)
    s = RE_HASH.sub("", s)
    for a, b in PUNCT_FIX.items():
        s = s.replace(a, b)
    s = s.strip().strip("\u3000").strip()
    return TEXT_PATCH.get(s, s)


def load():
    ents, _ = read_index(os.path.join(ISO, "SCRDATA.BIN"))
    d = open(os.path.join(ISO, "SCRDATA.ARC"), "rb").read()
    scripts = {e["name"]: d[e["off"]:e["off"] + e["usz"]] for e in ents}
    return [e["name"] for e in ents], scripts


def boot_table():
    """The engine's map-event script table inside the plain-ELF BOOT.BIN."""
    d = open(BOOT, "rb").read()
    p, out = BOOT_TABLE_OFF, []
    while p < len(d):
        e = d.find(b"\x00", p)
        if e < 0:
            break
        s = d[p:e].decode("cp932", "replace")
        if not NAME_RE.match(s):
            break
        ne = d.find(b"\x00", p + (e - p + 1 + 3) // 4 * 4)
        if ne < 0 or not NAME_RE.match(d[p + (e - p + 1 + 3) // 4 * 4:ne].decode("cp932", "replace")):
            break
        out.append(s)
        p += (e - p + 1 + 3) // 4 * 4
    return out


def calls(name, scripts, ops_set=(0x1D, 0x1E)):
    """0x1e / 0x1d call targets, in source order."""
    res, _ = disasm(scripts[name])
    out = []
    for off, op, size, ident, ops in res:
        if op in ops_set:
            ss = [v for t, v in ops if t == 3]
            if ss:
                out.append(ss[0])
    return out


def build_order(names, scripts):
    idx = {n.upper(): n for n in names}
    emitted, order = set(), []

    def add(n):
        k = n.upper()
        real = idx.get(k[:-4] if k.endswith(".SCR") else k)
        if not real or real.upper() in EXCLUDE or real.upper() in emitted:
            return
        emitted.add(real.upper())
        order.append(real)

    # 1. オープニング: PRG_OPENING's call order
    #    (OP_TAT_01..18 + interleaved M_14/M_41 ; OP_HTM_01..18 + interleaved F_03/F_11/F_20)
    for n in calls("PRG_OPENING", scripts):
        add(n)
    # 2. the engine's own map-event table order (M_/S_/F_/MEET/SEL/V/H_*/T_*/…)
    for n in boot_table():
        add(n)
    # 3. エンディング: PRG_ENDING's call order (EP_* …)
    for n in calls("PRG_ENDING", scripts):
        add(n)
    # 3b. PRG_MESS = map-command monologue (the only system script holding real 台詞)
    add("PRG_MESS")
    # 4. everything else, in LSDARC index order
    for n in names:
        add(n)
    return order


def script_lines(name, scripts):
    res, _ = disasm(scripts[name])
    for off, op, size, ident, ops in res:
        if op == 0x5A:
            for t, v in ops:
                if t == 3:
                    yield clean(v)
        elif op == 0x5C:
            ss = [v for t, v in ops if t == 3]
            first = ops[0] if ops else None
            if first and first[0] == 1 and re.fullmatch(r"[0-9a-f]{8}", first[1]) \
                    and int(first[1], 16) == len(ss):
                pass  # operand[0] is the choice count
            for s in ss:
                txt = s.rsplit(",", 1)[0] if "," in s else s
                txt = clean(txt)
                if txt:
                    yield txt


if __name__ == "__main__":
    names, scripts = load()
    # verify every TEXT_PATCH key really is a unique whole line (abort otherwise)
    raw = []
    for n in scripts:
        res, _ = disasm(scripts[n])
        for off, op, size, ident, ops in res:
            if op == 0x5A:
                raw += [v for t, v in ops if t == 3]
    for k in TEXT_PATCH:
        c = sum(1 for s in raw if k in s)
        assert c == 1, f"TEXT_PATCH key occurs {c}x: {k!r}"
    order = build_order(names, scripts)
    outfile = sys.argv[1] if len(sys.argv) > 1 else None
    lines, per = [], []
    for n in order:
        c = 0
        for t in script_lines(n, scripts):
            lines.append(t)
            c += 1
        per.append((n, c))
    print(f"# {len(order)} scripts, {len(lines)} lines")
    if outfile:
        os.makedirs(os.path.dirname(outfile), exist_ok=True)
        with io.open(outfile, "w", encoding="utf-8-sig", newline="\n") as f:
            for l in lines:
                f.write(l + "\n")
        with io.open(outfile + ".scripts.txt", "w", encoding="utf-8") as f:
            for n, c in per:
                f.write(f"{n}\t{c}\n")
        print("# wrote", outfile)
    else:
        for l in lines[:40]:
            print(l)
