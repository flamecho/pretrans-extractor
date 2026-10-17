#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""for Symphony ポータブル (PSP-JP, Takuyo, ULJM05258, v1.01) full-text extractor.

Takuyo gss family (same as himehibi / littleaid / etude prologue):
  container : LSDARC V.100   SCRDATA.BIN index + SCRDATA.ARC payload
                               1402 scripts, all isPacked=0, offset chain OK
  script    : "SCR 1.10"     u16 opcode | u8 size | u16 id | operand*
                             (byte-identical layout to SCR 2.00; 1402/1402 exact coverage)

Text opcodes (verified on this title):
  0x5a  message-box text                  -> one click = one line
  0xfc  message-box text with %s slots    -> slot list follows the string (0xffffffff terminated)
  0x5c  choices  (u32 count, "『text』,LABEL", ...)
  0xfd  slot writes (speaker plate a003, image c803, ...)  -> not displayed text, dropped
  0x1e/0x1d  script calls (script + label)

Two protagonists, sex chosen at start (MAN_START.SCR / WOMAN_START.SCR):
  藤井 和真 (male) / 藤井 悠希 (female) -- ELF name-entry defaults.
  slots: 0c02 = given name, 2002 = surname   ("%s%s" with [2002,0c02] = 藤井和真)

Route / play order = the dispatch tables themselves:
  male   : M_SPRING(P_*) M_SUMMER(S_*) {M_AA_AUT(A_AA*) M_AA_WIN(W_AA*) ED_AA} .. AA..EE
  female : W_SPRING(P_*) W_SUMMER(S_*) {W_FF_AUT(A_FF*) W_FF_WIN(W_FF*) ED_FF} .. FF..JJ
  P_=spring S_=summer A_=autumn W_=winter ; letter code = character, digits = scene no.
"""
import os
import re
import sys
import io
import argparse
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gss_lsdarc as L
import himehibi_disasm as D

GIVEN = {"male": "\u548c\u771f", "female": "\u60a0\u5e0c"}   # 和真 / 悠希
SURNAME = "\u85e4\u4e95"                                       # 藤井

SYSTEM = {
    "AUTOEXEC", "AUTOSELECT", "DEBUG", "FADE", "INIT", "LOOP", "MAIN", "NAME",
    "OPTION", "RELOAD", "SELECT", "SETEST", "SOUND", "STAFF", "YURASHI",
    "MAN_START", "WOMAN_START",
}

RE_LINEBREAK = re.compile(r"\\n")
RE_CTRL = re.compile(r"\\[a-zA-Z]")
RE_CONV = re.compile(r"%[0-9.\-]*s")

DISPATCH = {
    "male": [["M_SPRING"], ["M_SUMMER"]] +
            [["M_%s_AUT" % c, "M_%s_WIN" % c, "ED_%s" % c]
             for c in ("AA", "BB", "CC", "DD", "EE")],
    "female": [["W_SPRING"], ["W_SUMMER"]] +
              [["W_%s_AUT" % c, "W_%s_WIN" % c, "ED_%s" % c]
               for c in ("FF", "GG", "HH", "II", "JJ")],
}


def clean(s):
    s = RE_LINEBREAK.sub("", s)
    s = RE_CTRL.sub("", s)
    return s.strip().strip("\u3000").strip()


def load(datadir):
    ents, _ = L.read_index(os.path.join(datadir, "SCRDATA.BIN"))
    arc = open(os.path.join(datadir, "SCRDATA.ARC"), "rb").read()
    return ents, {e["name"]: L.unpack_entry(arc, e) for e in ents}


def calls_of(blob):
    out = []
    for off, op, size, ident, o in D.disasm(blob)[0]:
        if op in (0x1D, 0x1E):
            ss = [v for t, v in o if t == 3]
            if ss:
                out.append(ss[0])
    return out


def norm(n):
    k = n.upper()
    return k[:-4] if k.endswith(".SCR") else k


def subst(s, ops, slots):
    vals = []
    for t, v in ops:
        if t == 1 and v == "ffffffff":
            break
        if t == 6:
            vals.append(slots.get(v, ""))
        elif t == 3:
            vals.append(v)
    it = iter(vals)
    return RE_CONV.sub(lambda m: next(it, ""), s)


def extract_script(blob, slots):
    res, err = D.disasm(blob)
    if err:
        raise RuntimeError("disasm failed: %s" % (err,))
    for off, op, size, ident, o in res:
        if op == 0x5A:
            for t, v in o:
                if t == 3:
                    yield ("msg", clean(v))
        elif op == 0xFC:
            si = next((i for i, (t, v) in enumerate(o) if t == 3), None)
            if si is not None:
                yield ("msg", clean(subst(o[si][1], o[si + 1:], slots)))
        elif op == 0x5C:
            for t, v in o:
                if t != 3:
                    continue
                body = v.rsplit(",", 1)[0]
                if clean(body):
                    yield ("choice", clean(body))


def build_order(names, S, calls, report):
    idx = {norm(n): n for n in names}
    order, owner = [], {}
    for route in ("male", "female"):
        for block in DISPATCH[route]:
            for d in block:
                real = idx.get(norm(d))
                if not real:
                    report.append("MISSING dispatcher %s (%s)" % (d, route))
                    continue
                if d.startswith("ED_"):
                    if real not in owner:
                        owner[real] = route
                        order.append(real)
                    continue
                n0 = len(order)
                for c in calls[real]:
                    t = idx.get(norm(c))
                    if not t or t in owner:
                        continue
                    owner[t] = route
                    order.append(t)
                if len(order) == n0:
                    report.append("EMPTY dispatcher %s (%s)" % (d, route))
    leftover = [n for n in names if n not in owner
                and n.split("_")[0] in ("P", "S", "A", "W", "ED")]
    return order, owner, leftover


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("datadir", nargs="?",
                    default=os.path.join(HERE, "..", "_src_fsymph", "iso", "PSP_GAME", "USRDIR"))
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()

    ents, S = load(a.datadir)
    names = [e["name"] for e in ents]
    calls = {n: calls_of(b) for n, b in S.items()}
    report = []
    order, owner, leftover = build_order(names, S, calls, report)

    out, per, kinds = [], [], collections.Counter()
    for name in order:
        if norm(name) in SYSTEM:
            continue
        slots = {"0c02": GIVEN[owner[name]], "2002": SURNAME}
        n0 = len(out)
        for kind, txt in extract_script(S[name], slots):
            if not txt:
                continue
            out.append(txt)
            kinds[kind] += 1
        per.append((name, owner[name], len(out) - n0))

    with io.open(a.out, "w", encoding="utf-8-sig", newline="\n") as f:
        for line in out:
            f.write(line + "\n")
    work = os.path.join(HERE, "..", "_work_fsymph")
    os.makedirs(work, exist_ok=True)
    with io.open(os.path.join(work, "scripts.txt"), "w", encoding="utf-8", newline="\n") as f:
        for n, rt, c in per:
            f.write("%s\t%s\t%d\n" % (n, rt, c))
        for n in leftover:
            f.write("%s\t%s\t%d\n" % (n, "LEFTOVER", 0))

    miss = [n for n in names if n not in owner and norm(n) not in SYSTEM]
    print("scripts used %d / %d   lines %d   %s" % (len(per), len(ents), len(out), dict(kinds)))
    print("unused story scripts (%d): %s" % (len(miss), miss))
    for r in report:
        print("!", r)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
