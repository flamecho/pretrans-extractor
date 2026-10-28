#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""月影の鎖 -錯乱パラノイア- (NS-JP) text extract ---- TAKUYO gss / SCR 2.00.

Chain: NSP(PFS0) -> Program NCA (titlekey = tik[0x180:0x190] raw) -> RomFS
       -> SCRDATA.BIN/.ARC (LSDARC V.100, all plaintext) -> SCR 2.00 disasm -> lines.

Line rules (skill §0):
  0x5a  message box text        -> one click = one line ; \n = in-box soft wrap (merge)
  0xfc  message box with %s     -> %s <- protagonist name slots 1802/0c02
  0xf0  title card (扉文)        -> displayed
  0x5c  choices                 -> "text ,FLAG" ; text = before last ASCII comma
  \c    page clear + wait       -> break into a new line (L0, same engine family)
  @r..@0 / @r#rBASE|READING#@0  -> emphasis / ruby markup : keep BASE only
"""
import sys, os, re, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from himehibi_lsdarc import read_index
from himehibi_disasm import disasm

ROMFS = os.path.join(VNTRANS_HOME, "_work_tsuki/romfs")
OUT = os.path.join(VNTRANS_HOME, "提取结果/[NS-JP]月影の鎖 -錯乱パラノイア-.txt")

# protagonist default name (PRG_ROUTE 0x132: slot 1802 <- 冬浦 , 0c02 <- めぐみ)
NAME_SLOTS = {"1802": "冬浦", "0c02": "めぐみ"}

SYSTEM = {"AUTOEXEC", "DEBUG", "INIT", "RELOAD", "SELECT2", "CERO_VITA",
          "PRG_BG", "PRG_EFFECT", "PRG_NAME", "PRG_PLATE", "PRG_ROUTE", "PRG_STAND"}

RE_RUBY = re.compile(r"#r([^|#]*)\|[^#]*#")   # ruby: #rBASE|READING#  -> BASE
RE_HL = re.compile(r"@r(.*?)@0", re.S)        # emphasis: @r...@0      -> ...
RE_CTRL = re.compile(r"\\[a-zA-Z]")

ents, _ = read_index(os.path.join(ROMFS, "SCRDATA.BIN"))
arc = open(os.path.join(ROMFS, "SCRDATA.ARC"), "rb").read()
SCR = {e["name"].upper(): arc[e["off"]:e["off"] + e["usz"]] for e in ents}
CODE = {n: disasm(b)[0] for n, b in SCR.items()}

# ---- order : PRG_ROUTE call sequence (com -> mainside -> kag -> mot -> ino -> har) ----
order = []
for off, op, size, ident, o in CODE["PRG_ROUTE"]:
    if op == 0x1e and len(o) >= 2 and o[0][0] == 3 and o[0][1].lower().endswith(".scr"):
        nm = o[0][1].upper()[:-4]
        if nm in SCR and nm not in order:
            order.append(nm)

lines = []
stats = collections.Counter()


def markup(s):
    s = RE_RUBY.sub(r"\1", s)
    s = RE_HL.sub(r"\1", s)
    s = s.replace("@r", "").replace("#@0", "").replace("@0", "")
    return s


def clean(s):
    s = markup(s)
    s = s.replace("\\n", "")        # in-box soft wrap -> merge
    s = RE_CTRL.sub("", s)          # any residual \x control code
    return s


def fmt(s, ops, slots):
    args = [slots.get(v, "") for t, v in ops[1:] if t == 6]
    out, k = [], 0
    for i, ch in enumerate(s):
        if s.startswith("%s", i) and k < len(args):
            out.append(args[k]); k += 1
        elif s.startswith("%s", i):
            out.append("")
        else:
            if i and s[i - 1] == "%" and ch == "s":
                continue
            out.append(ch)
    return "".join(out).replace("%%", "%")


prev = [None, None]


def emit(op, s, dedup=False):
    """Twin forms of one message:
    (a) 0x5a fixed name / 0xfc %s  -> same sentence, keep one (cross-op only);
    (b) voice on/off branch       -> 0x22/0x21 goto + 0x23 label wrap an identical
        instruction on the other path; a single run shows ONE == dedupe (L0 byte-identical text op).
    """
    if s and prev[1] == s and (dedup or (op != prev[0] and "fc" in (op, prev[0]))):
        return False
    lines.append(s)
    prev[0], prev[1] = op, s
    return True


for name in order:
    if name in SYSTEM:
        continue
    slots = dict(NAME_SLOTS)
    seen_cond = seen_lbl = False
    for off, op, size, ident, o in CODE[name]:
        if op in (0x22, 0x21):
            seen_cond = True
        elif op == 0x23:
            seen_lbl = True
        branch = seen_cond and seen_lbl
        if op == 0xfd:
            if len(o) >= 2 and o[0][0] == 6:
                tgt = o[0][1]
                if tgt in ("2402", "3402"):      # independent name window -> drop
                    continue
                if o[1][0] == 3:
                    slots[tgt] = o[1][1]
            continue
        if op == 0x5a:
            stats["op5a"] += 1
            segs = [clean(x).strip("\u3000 ") for x in o[0][1].split("\\c")]
            stats["seg_c"] += len(segs) - 1
            for k, seg in enumerate(segs):
                if seg:
                    if not emit("5a", seg, branch and k == 0):
                        stats["dedup"] += 1
                    else:
                        stats["text"] += 1
            seen_cond = seen_lbl = False
        elif op == 0xfc:
            stats["opfc"] += 1
            segs = [clean(x).strip("\u3000 ") for x in fmt(o[0][1], o, slots).split("\\c")]
            stats["seg_c"] += len(segs) - 1
            for k, seg in enumerate(segs):
                if seg:
                    if not emit("fc", seg, branch and k == 0):
                        stats["dedup"] += 1
                    else:
                        stats["text"] += 1
            seen_cond = seen_lbl = False
        elif op == 0xf0:
            stats["op_f0"] += 1
            txt = clean(o[0][1]).strip()
            if txt:
                lines.append(txt)
                stats["title"] += 1
        elif op == 0x5c:
            stats["op_5c"] += 1
            n = int.from_bytes(bytes.fromhex(o[0][1]), "little")
            for t, v in o[1:1 + n]:
                txt = slots.get(v, "") if t == 6 else v
                txt = txt.rsplit(",", 1)[0].rstrip()
                if txt:
                    lines.append(txt)
                    stats["option"] += 1

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8-sig", newline="\n") as f:
    f.write("\n".join(lines) + "\n")
print("scripts", len([n for n in order if n not in SYSTEM]),
      "skipped", [n for n in order if n in SYSTEM])
print("lines", len(lines), dict(stats))
