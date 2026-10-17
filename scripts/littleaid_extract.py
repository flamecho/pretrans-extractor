#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Little Aid Portable (PSP-JP, 2007 Takuyo, ULJM-05...) full-text extractor.

Same engine family as himehibi / Cafe Cuillere / etude prologue (Takuyo gss):
  container : LSDARC V.100  (SCRDATA.BIN index + SCRDATA.ARC payload)
  script    : "SCR 1.10"   (older than the PSV 'SCR 2.00' but the instruction
                            encoding is byte-identical:
                            u16 opcode | u8 size | u16 id | operand*
                            operand type 0x01/0x05->4B, 0x02/0x04/0x06->2B,
                                          0x03->NUL-terminated CP932 string)
              all 622 scripts disassemble with 622/622 exact size coverage.

Displayed-text opcodes (verified on this title):
  0x5a  message-box text                       -> one click = one line
  0xfc  message-box text with %s               -> substitution slots follow the string
  0xfd  (6,5752)<--(3,title) / slot build       -> 0x5802 = per-scene title card
  0x5c  choices  (u32 count, "<value>text,LABEL", ...) -> option text
  0x107 slot += literal/slot                     (used only to assemble the title)

Excluded: 0xfd speaker name plate (0c02), place plate (1804), background (d803),
          0x3c/0x3d SE/BGM, 0x3b/0x10c/0x107 images, 0x1d/0x1e calls, variables/flags.

Protagonist (renameable): 西村 あかり.  eboot (BOOT.BIN = PLAIN ELF) name-entry
default block = ["西村"]["あかり"]["西"].
  slot 0x1c02 = あかり   (evidence: 「%sちゃん」, title 「届かない知らせと<1c02>の不安」)
  slot 0x3002 = 西村     (evidence: 「%s%s」 self-intro = 西村あかり, 「%sさん」)
  slot 0x4402 = 西       (3rd name-entry field; ONLY used by 沢登 with 「%sくん」)
Use --slot 4402=西村 to override if the third field is judged to be the full surname.

Story order = STORYCTRL.SCR's own 0x1e dispatch table (637 calls, covering every
reachable script: 共通 -> 早乙女 -> 匣 -> 土師 -> ふみ -> 砕我 -> 花邑 -> 風紀
-> 堤 -> 沢登).  Scripts reachable from nowhere (UMA017/021/028/031/039/038旧) are
older duplicates kept in the archive and are excluded.
"""
import sys, os, re, io, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gss_lsdarc as L
import himehibi_disasm as D

SLOT = {"1c02": "\u3042\u304b\u308a", "3002": "\u897f\u6751", "4402": "\u897f"}

# System / UI / debug scripts (no story text).  MAIN = route-skip DEBUG menu,
# BG/SUB = transition + debug notes, the rest = boot / save / effect plumbing.
SYSTEM = {
    "AUTOEXEC", "INIT", "INITFLG", "MAIN", "BG", "DAY", "FINEND", "MEMAI",
    "RELOAD", "SELECT", "SETPOCKETBOOK", "STORYCTRL", "SUB", "THREAD", "WALK",
    "YURASHI", "DEBUG",
}
# present in the archive but referenced by nothing (superseded duplicates)
DEAD = {"UMA017", "UMA021", "UMA028", "UMA031", "UMA039", "UMA038\u65e7"}

RE_LINEBREAK = re.compile(r"\\n")               # in-box line break -> merge
RE_CTRL = re.compile(r"\\[a-zA-Z]")             # \c -> drop
RE_AT = re.compile(r"@[A-Za-z0-9]")             # @R/@r/@0 ... -> drop
RE_CONV = re.compile(r"%[0-9.\-]*[a-zA-Z]")     # %s
RE_OPTNUM = re.compile(r"^0x[0-9A-Fa-f]{1,4}")  # option value prefix (not displayed)

# Whole-line fixes for authoring typos proven to be in the ORIGINAL script bytes
# (unclosed 「 in a box that clearly ends there / mis-typed 」).  Each key must be
# present exactly once after cleaning, otherwise the extractor aborts.
TEXT_PATCH = {
    # COM092-5 : inner 『…』 closed correctly, outer quote mis-typed as 』
    "\u300c\u3046\u3093\u3001\u3053\u308c\u3001\u5824\u304f\u3093\u304b\u3089\u805e\u3044\u305f\u3093\u3060\u3051\u3069\u3001"
    "\u4f55\u3067\u3082\u300e\u925b\u7b46\u3092\u9069\u5f53\u306b\u8ee2\u304c\u3057\u3066\u305f\u3089\u6b63\u89e3\u3057\u305f"
    "\u300f\u3063\u3066\u3044\u3063\u3066\u305f\u3093\u3067\u3059\u3063\u3066\u300f":
    "\u300c\u3046\u3093\u3001\u3053\u308c\u3001\u5824\u304f\u3093\u304b\u3089\u805e\u3044\u305f\u3093\u3060\u3051\u3069\u3001"
    "\u4f55\u3067\u3082\u300e\u925b\u7b46\u3092\u9069\u5f53\u306b\u8ee2\u304c\u3057\u3066\u305f\u3089\u6b63\u89e3\u3057\u305f"
    "\u300f\u3063\u3066\u3044\u3063\u3066\u305f\u3093\u3067\u3059\u3063\u3066\u300d",
    # BADYUZ001 : 沢登 shouted line, closing 」 missing
    "\u300c\u30b3\u30e9\u2015\u2015\u2015\uff01\uff01\uff01":
    "\u300c\u30b3\u30e9\u2015\u2015\u2015\uff01\uff01\uff01\u300d",
    # YUZ027-A : 沢登 sobbing line between two closed boxes, closing 」 missing
    "\u300c\u304a\u6bcd\u3055\u3093\u2026\u2026":
    "\u300c\u304a\u6bcd\u3055\u3093\u2026\u2026\u300d",
}


def clean(s):
    s = RE_LINEBREAK.sub("", s)
    s = RE_CTRL.sub("", s)
    s = RE_AT.sub("", s)
    return s.strip().strip("\u3000").strip()


def clean_title(s):
    return s.strip().strip("\u3000").strip()


def subst_string(s, ops):
    subs = []
    for t, v in ops:
        if t == 1 and v == "ffffffff":
            break
        if t == 6:
            subs.append(SLOT.get(v, ""))
        elif t == 3:
            subs.append(v)
    it = iter(subs)
    return RE_CONV.sub(lambda m: next(it, ""), s)


def load(datadir):
    ents, _ = L.read_index(os.path.join(datadir, "SCRDATA.BIN"))
    return ents, {e["name"]: L.unpack_entry(
        open(os.path.join(datadir, "SCRDATA.ARC"), "rb").read(), e) for e in ents}


def calls(blob):
    res, _ = D.disasm(blob)
    out = []
    for off, op, size, ident, ops in res:
        if op in (0x1D, 0x1E):
            ss = [v for t, v in ops if t == 3]
            if ss:
                out.append(ss[0])
    return out


def build_order(names, S):
    idx = {n.upper(): n for n in names}
    seen, order = set(), []

    def add(n):
        k = n.upper()
        if k.endswith(".SCR"):
            k = k[:-4]
        real = idx.get(k)
        if not real or real.upper() in seen:
            return
        seen.add(real.upper())
        order.append(real)
        for c in calls(S[real]):
            add(c)

    add("STORYCTRL")
    for n in names:                       # any stragglers, archive order
        add(n)
    return order


def extract_script(blob):
    """Yield (kind, text) in instruction order: title / msg / choice."""
    res, err = D.disasm(blob)
    if err:
        raise RuntimeError("disasm failed: %s" % (err,))
    slots = dict(SLOT)
    title = None
    title_set = False
    for off, op, size, ident, ops in res:
        if op == 0xFD and len(ops) == 2 and ops[0][0] == 6:
            dst = ops[0][1]
            if ops[1][0] == 3:
                slots[dst] = clean(ops[1][1])
            elif ops[1][0] == 6:
                slots[dst] = slots.get(ops[1][1], "")
            if dst == "5802":
                title_set = True
        elif op == 0x107 and len(ops) == 2 and ops[0][0] == 6:
            dst = ops[0][1]
            v = clean(ops[1][1]) if ops[1][0] == 3 else slots.get(ops[1][1], "")
            slots[dst] = slots.get(dst, "") + v
        elif op == 0x5A:
            if title_set and title is None:
                title = slots.get("5802", "")
                if title:
                    yield ("title", clean_title(title))
            for t, v in ops:
                if t == 3:
                    yield ("msg", clean(v))
        elif op == 0xFC:
            if title_set and title is None:
                title = slots.get("5802", "")
                if title:
                    yield ("title", clean_title(title))
            si = next((i for i, (t, v) in enumerate(ops) if t == 3), None)
            if si is not None:
                yield ("msg", clean(subst_string(ops[si][1], ops[si + 1:])))
        elif op == 0x5C:
            for t, v in ops:
                if t != 3:
                    continue
                body = v.rsplit(",", 1)[0]
                body = RE_OPTNUM.sub("", body, count=1)
                if clean(body):
                    yield ("choice", clean(body))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("datadir", nargs="?", default=os.path.join(HERE, "..", "_work_littleaid"))
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--slot", action="append", default=[],
                    help="override a name slot, e.g. --slot 4402=\u897f\u6751")
    a = ap.parse_args()
    for s in a.slot:
        k, v = s.split("=", 1)
        SLOT[k] = v

    ents, S = load(a.datadir)
    names = [e["name"] for e in ents]
    order = build_order(names, S)
    out, per, kinds = [], [], {}
    for name in order:
        if name.upper() in SYSTEM or name.upper() in DEAD:
            continue
        n0 = len(out)
        for kind, txt in extract_script(S[name]):
            if not txt:
                continue
            out.append(txt)
            kinds[kind] = kinds.get(kind, 0) + 1
        per.append((name, len(out) - n0))

    for k in TEXT_PATCH:
        c = sum(1 for x in out if x == k)
        assert c == 1, "TEXT_PATCH key occurs %dx: %r" % (c, k)
    out = [TEXT_PATCH.get(x, x) for x in out]

    with io.open(a.out, "w", encoding="utf-8-sig", newline="\n") as f:
        for l in out:
            f.write(l + "\n")
    with io.open(a.out + ".scripts.txt", "w", encoding="utf-8") as f:
        for n, c in per:
            f.write("%s\t%d\n" % (n, c))
    print("scripts %d/%d   lines %d   kinds %s" % (len(per), len(ents), len(out), kinds))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
