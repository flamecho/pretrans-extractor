#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""星色のおくりもの (PSP-JP, 2008 Takuyo) full-text extractor.

Engine: Takuyo gss family
  container : LSDARC V.100  (USRDIR/SCRDATA.BIN index + SCRDATA.ARC payload; 269 entries,
                              all isPacked=0, offset chain 0-offset verified)
  script    : "SCR 2.00"  (u16 opcode | u8 size | u16 id | operand*;
                            type 0x01/0x05->4B, 0x02/0x04/0x06->2B, 0x03->NUL-term CP932)
              269/269 scripts disassemble with exact size coverage.

Displayed text opcodes:
  0x5a  message box text                     -> one click = one line
  0xfc  message box text with %s             -> substitution slots follow the string
  0xf0  scene title card (literal string)    -> 187 in story
  0x5c  choices  (u32 count, "text,LABEL", ...) -> text before last ASCII comma

Not collected: 0xfd slot writes (name plate d402 <- 8480 / background / sprite),
  0x3c/0x3d SE/BGM, 0x3b images, 0x1d/0x1e calls, 0x107 slot +=, variables/flags.

Story order = PRG_ROUTE.SCR's own 0x1e dispatch list (378 calls; 高師 -> 紳 -> 誠悟 ->
宗哉 routes, 09/10/11/12 + EP), dedup keeping first occurrence.  EP_ALL_EP (grand ending,
called from PRG_EYE-CATCH) is appended last.

Protagonist (renameable) = 由本 桜衣, proven by DEBUG's slot seeding:
  0xfd (6,4c03)="桜衣"  (given name; 「%sちゃん」/「%sさん」)
  0xfd (6,5803)="由本"  (surname; 「%sさん」/ self-intro 「%s%s」)
  0xfd (6,8480)="　　由本　桜衣　　" (name plate)
"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import io
import sys
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gss_lsdarc as L
import himehibi_disasm as D

NAME_GIVEN = "\u685c\u8863"   # 桜衣
NAME_FAMILY = "\u7531\u672c"  # 由本
SLOT = {"4c03": NAME_GIVEN, "5803": NAME_FAMILY}

RE_BREAK = re.compile("\\\\n[\u3000]*")
RE_CTRL = re.compile(r"\\[a-zA-Z]")
RE_AT = re.compile(r"@[A-Za-z0-9]")
RE_HASH = re.compile(r"#[A-Za-z0-9]+#")
RE_CONV = re.compile(r"%[0-9.\-]*[a-zA-Z]")

# Authoring typo proven in the ORIGINAL script bytes: the monologue box opens with
# U+FF08 （ but closes with U+300D 」 (bytes ...8169 ...8176).  Each key must occur
# exactly once in the cleaned stream, otherwise the run aborts.
TEXT_PATCH = {
    "\uff08\u305d\u308c\u3067\u3001\u305d\u306e\u3046\u3061\u79c1\u306e\u59ff\u3092"
    "\u898b\u5931\u3063\u3066\u2026\u2026\u300d":
    "\uff08\u305d\u308c\u3067\u3001\u305d\u306e\u3046\u3061\u79c1\u306e\u59ff\u3092"
    "\u898b\u5931\u3063\u3066\u2026\u2026\uff09",
}

# scripts that carry no displayed text (boot / save / effect / debug)
SYSTEM = {
    "AUTOEXEC", "INIT", "PRG_NAME", "PRG_STAND", "PRG_ROUTE", "PRG_BG",
    "PRG_EFFECT", "PRG_EFFECTSTOP", "PRG_EYE-CATCH", "PRG_FEELING", "SELECT",
    "SELECT2", "YURASHI", "CERO", "RELOAD", "SEGA", "DEBUG",
    "PRG_FORTUNETEXT",           # dispatcher only, no 0x5a
}

# 星占い / 相性占い result banks — menu-driven but their text IS rendered in a
# message box, so they are collected AFTER the story (archive index order).
# PRG_HOSHITEXT = 「今日の運勢」one-liners; PRG_{NON,TAK,SEI,SIN,SOU}_* = 好感度占い.
EXTRA_PREFIX = ("PRG_HOSHITEXT", "PRG_NON_", "PRG_TAK_", "PRG_SEI_", "PRG_SIN_", "PRG_SOU_")


def clean(s):
    s = RE_BREAK.sub("", s)
    s = RE_CTRL.sub("", s)
    s = RE_AT.sub("", s)
    s = RE_HASH.sub("", s)
    return s.strip().strip("\u3000").strip()


def subst(s, ops):
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
    ents, arc = L.load(os.path.join(datadir, "SCRDATA.BIN"),
                       os.path.join(datadir, "SCRDATA.ARC"))
    out = {}
    for e in ents:
        out.setdefault(e["name"], arc[e["off"]:e["off"] + e["usz"]])
    return [e["name"] for e in ents], out


def call_list(blob):
    res, err = D.disasm(blob)
    assert err is None, err
    out = []
    for off, op, size, ident, ops in res:
        if op in (0x1D, 0x1E):
            ss = [v for t, v in ops if t == 3]
            if ss:
                out.append(ss[0])
    return out


def build_order(names, S):
    idx = {n.upper(): n for n in names}
    order, seen = [], set()

    def norm(n):
        k = n.upper()
        for suf in (".SCR", ".PRG"):
            if k.endswith(suf):
                k = k[:-4]
        return k

    for n in call_list(S["PRG_ROUTE"]):
        k = norm(n)
        real = idx.get(k) or idx.get(k + ".SCR")
        if real and real.upper() not in seen:
            seen.add(real.upper())
            order.append(real)
    for extra in ("EP_ALL_EP",):          # grand ending
        real = idx.get(extra)
        if real and real.upper() not in seen:
            seen.add(real.upper())
            order.append(real)
    # 星占い result banks: append in archive index order (after the story)
    for n in names:
        if n.upper().startswith(EXTRA_PREFIX) and n.upper() not in seen \
                and n.upper() not in SYSTEM:
            seen.add(n.upper())
            order.append(n)
    return order


# --- キャラクター資料（プロフィール画面）------------------------------------
# Not in SCRDATA: the whole block lives in BOOT.BIN (plain ELF) as NUL-terminated
# CP932 strings, 0x7a8dc..0x7ae5c:
#   <名前>\n（<よみ>） / 年齢 / 誕生日 / 血液型 / 星座 / 身長 / 体重 /
#   好き / 苦手 / (comment slot1) / (comment slot2)
# 8 characters: 稲船隆志・明戸紳・鳴滝誠悟・鳴滝宗哉・明戸美海・明戸真由・吉田茉莉・葛涼子
# The block ends at the first ASCII-only resource id ("pro_takashi").
PROFILE_BASE = 0x7A000
PROFILE_MIN, PROFILE_MAX = 0x7A000, 0x7C000


def _cstr(d, i):
    j = d.index(b"\x00", i)
    if j <= i:
        return "", j + 1
    try:
        return d[i:j].decode("cp932"), j + 1
    except UnicodeDecodeError:
        return None, j + 1


def clean_prof(s):
    """Profile strings use REAL 0x0A newlines (not the script's '\\n' escape)."""
    s = s.replace("\n", "")
    s = RE_CTRL.sub("", s)
    return s.strip().strip("\u3000").strip()


def extract_profile(boot):
    d = open(boot, "rb").read()
    i, start = PROFILE_BASE, None
    while i < PROFILE_MAX:                      # locate the first name/reading block
        s, i = _cstr(d, i)
        if s and "\n（" in s and s.endswith("）"):
            start = i - (len(s.encode("cp932")) + 1)
            break
    if start is None:
        raise RuntimeError("profile block not found in %s" % boot)
    out, i = [], start
    end = d.find(b"pro_takashi", start)          # first resource id after the block
    if end < 0:
        end = PROFILE_MAX
    while i < end:
        s, i = _cstr(d, i)
        if s is None:
            continue
        t = clean_prof(s)
        if t:
            out.append(t)
    return out



def extract(blob):
    """Yield (kind, text) in instruction order.

    Slot state machine: 星占い scripts build the paragraph in a slot with
    `0xfd (6,dst)(3,str)` (=) and `0x107 (6,dst)(3,str)` (+=), then print it
    with `0xfc (6,dst)` (no literal string operand).  Story scripts never use
    `0x107`, and their `0xfd` only writes the name plate, so this is harmless.
    """
    res, err = D.disasm(blob)
    assert err is None, err
    slots = dict(SLOT)
    for off, op, size, ident, ops in res:
        if op == 0x5A:
            for t, v in ops:
                if t == 3:
                    yield ("msg", clean(v))
        elif op == 0xFC:
            si = next((i for i, (t, v) in enumerate(ops) if t == 3), None)
            if si is not None:
                yield ("msg", clean(subst(ops[si][1], ops[si + 1:])))
            elif ops and ops[0][0] == 6:
                yield ("msg", clean(slots.get(ops[0][1], "")))
        elif op == 0xF0:
            for t, v in ops:
                if t == 3:
                    yield ("title", clean(v))
        elif op == 0x5C:
            for t, v in ops:
                if t != 3:
                    continue
                body = v.rsplit(",", 1)[0]
                if clean(body):
                    yield ("choice", clean(body))
        elif op in (0xFD, 0x107) and len(ops) >= 2 and ops[0][0] == 6:
            dst, src = ops[0][1], ops[1]
            if src[0] == 3:
                val = src[1]
            elif src[0] == 6:
                val = slots.get(src[1], "")
            else:
                continue
            slots[dst] = val if op == 0xFD else slots.get(dst, "") + val


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datadir", default=os.path.join(VNTRANS_HOME, "_src_hoshiiro/PSP_GAME/USRDIR"))
    ap.add_argument("--boot", default=os.path.join(VNTRANS_HOME, "_src_hoshiiro/PSP_GAME/SYSDIR/BOOT.BIN"))
    ap.add_argument("--no-profile", action="store_true", help="skip the BOOT.BIN profile block")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--slot", action="append", default=[])
    a = ap.parse_args()
    for s in a.slot:
        k, v = s.split("=", 1)
        SLOT[k] = v

    names, S = load(a.datadir)
    order = build_order(names, S)
    out, per, kinds = [], [], {}
    for name in order:
        if name.upper() in SYSTEM:
            continue
        n0 = len(out)
        for kind, txt in extract(S[name]):
            if not txt:
                continue
            out.append(txt)
            kinds[kind] = kinds.get(kind, 0) + 1
        per.append((name, len(out) - n0))

    if not a.no_profile:
        n0 = len(out)
        out.extend(extract_profile(a.boot))
        kinds["profile"] = len(out) - n0
        per.append(("<BOOT.BIN:profile>", len(out) - n0))

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
    print("scripts used %d / %d entries   lines %d   kinds %s"
          % (len(per), len(names), len(out), kinds))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
