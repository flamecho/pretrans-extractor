#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cafe Cuillere (PSV PCSG01197, DWANGO/Takuyo, gss engine) text extractor.

Chain: LSDARC 'SCR 2.00' scripts -> displayed text (one click = one line).

Displayed-text opcodes (same family as himehibi / Takuyo gss):
  0x5a  message box text
  0xfc  message box text with %s  (substitution sources = operands after string)
  0xf0  scenario title card (扉文)
  0x5c  choice options  -> "<marker><text> ,<flag>"  (marker 0/1/2 = flag value)
  0x10c message text with %s, string = "%.1d %.1d VOICE.WAV <text>" (voicemail/mail)
Excluded: 0xfd (speaker name plate), 0x3b/0x107 (images), 0x3c/0x3d (audio),
          0x1d/0x1e (calls), and all system/UI scripts.

Name slots (defaults from eboot.bin name table: 姓=藤白 名=真緒 読み=まお):
  6402 -> 真緒   7002 -> 藤白   8402 -> まお
"""
import sys, os, re, io, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import himehibi_lsdarc as L
import himehibi_disasm as D

SLOT = {"6402": "真緒", "7002": "藤白", "8402": "まお"}

SYSTEM_SCRIPTS = {
    "AUTOEXEC", "INIT", "PRG_BG", "PRG_EFFECT", "PRG_EFFECTSTOP", "PRG_NAME",
    "PRG_ROUTE", "PRG_STAND", "PRG_PLATE", "PRG_THREAD", "RELOAD",
    "SELECT", "SELECT2", "YURASHI", "DEBUG",
}

RE_RUBY = re.compile(r"#r([^|#]+)\|([^#]+)#")          # #r base|reading #  -> base
RE_BSCODE = re.compile(r"\\[a-zA-Z]")                   # \n \c ... (any backslash code)
RE_ATCODE = re.compile(r"@[a-zA-Z]")                    # @y @w ...
RE_CONV = re.compile(r"%[0-9.\-]*[a-zA-Z]")
RE_VOICE = re.compile(r"\.WAV\s?(.*)$", re.S)

# Explicit whole-line patches for defects proven to be in the ORIGINAL script bytes
# (halfwidth ')' where the game opens with fullwidth '（'). One entry per affected line.
TEXT_PATCH = {
    "（この距離で見ると、いつも以上に心臓に悪い……)":
    "（この距離で見ると、いつも以上に心臓に悪い……）",
}


def clean(s):
    s = RE_RUBY.sub(lambda m: m.group(1), s)
    s = RE_BSCODE.sub("", s)        # includes \n (in-box line break -> merge)
    s = RE_ATCODE.sub("", s)
    return s.strip().strip("\u3000").strip()


def resolve_slot(slot):
    return SLOT.get(slot, "\u3014\u672a\u89e3\u6790:%s\u3015" % slot)   # 〔未解析:xxxx〕


def subst_string(s, ops):
    """Format string `s`; `ops` = operands that follow the string operand."""
    subs = []
    for t, v in ops:
        if t == 1 and v == "ffffffff":
            break
        if t == 6:
            subs.append(SLOT.get(v, ""))
        elif t == 3:
            subs.append(v)
        else:
            subs.append("")
    it = iter(subs)
    return RE_CONV.sub(lambda m: next(it, ""), s)


def load(datadir):
    ents, _ = L.read_index(os.path.join(datadir, "SCRDATA.BIN"))
    d = open(os.path.join(datadir, "SCRDATA.ARC"), "rb").read()
    return ents, {e["name"]: d[e["off"]:e["off"] + e["usz"]] for e in ents}


def extract_lines(name, blob):
    """Yield (kind, text) for one script in instruction order."""
    res, err = D.disasm(blob)
    if err:
        raise RuntimeError("disasm failed in %s: %s" % (name, err))
    for off, op, size, ident, ops in res:
        if op == 0x5a:
            ss = [v for t, v in ops if t == 3]
            if ss:
                yield ("msg", clean(ss[0]))
        elif op == 0xfc:
            ss = [v for t, v in ops if t == 3]
            if ss:
                body = subst_string(ss[0], ops[1:])
                yield ("msg", clean(body))
        elif op == 0xf0:
            ss = [v for t, v in ops if t == 3]
            if ss:
                yield ("title", clean(ss[0]))
        elif op == 0x10c:
            # ops = (dest_slot)(3,string)(args...) ; substitution args follow the STRING
            si = next((i for i, (t, v) in enumerate(ops) if t == 3), None)
            if si is None:
                continue
            s = ops[si][1]
            if ".WAV" in s:
                body = subst_string(s, ops[si + 1:])
                m = RE_VOICE.search(body)
                if m and clean(m.group(1)):
                    yield ("msg", clean(m.group(1)))
        elif op == 0x5c:
            ss = [v for t, v in ops if t == 3]
            for v in ss:
                body = v.rsplit(",", 1)[0]
                body = re.sub(r"^\s*[\uff10\uff11\uff12]", "", body)  # strip 0/1/2 flag-value marker
                if clean(body):
                    yield ("choice", clean(body))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("datadir")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--stats", action="store_true")
    a = ap.parse_args()

    ents, S = load(a.datadir)
    order = [e["name"] for e in ents]
    out = []
    per = []
    kinds = {}
    for name in order:
        if name in SYSTEM_SCRIPTS:
            continue
        n0 = len(out)
        for kind, txt in extract_lines(name, S[name]):
            if not txt:
                continue
            if out and out[-1] == txt:          # collapse mutually-exclusive variants
                continue
            out.append(txt)
            kinds[kind] = kinds.get(kind, 0) + 1
        per.append((name, len(out) - n0))

    out = [TEXT_PATCH.get(x, x) for x in out]

    with io.open(a.out, "w", encoding="utf-8-sig", newline="\n") as f:
        for l in out:
            f.write(l + "\n")

    if a.stats:
        print("scripts (story): %d / %d   lines: %d   kinds: %s"
              % (len(per), len(order), len(out), kinds))
        for n, c in per:
            print("   %-14s %5d" % (n, c))
    else:
        print("wrote %s : %d lines from %d scripts" % (a.out, len(out), len(per)))


if __name__ == "__main__":
    main()
