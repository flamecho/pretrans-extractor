#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Money Parasite 〜嘘つきな女〜 (TAKUYO gss / SCR 2.00) text extractor."""
import sys, os, struct, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from himehibi_lsdarc import read_index
from himehibi_disasm import disasm

ROMFS = os.path.join(VNTRANS_HOME, "_work_mp/romfs")
OUT = os.path.join(VNTRANS_HOME, "提取结果/[NS-JP]Money Parasite 〜嘘つきな女〜.txt")

SYSTEM = {"AUTOEXEC", "INIT", "RELOAD", "SELECT2", "MINI_SELECT", "MINI_SELECT2",
          "DEBUG", "PRG_BG", "PRG_EFFECT", "PRG_NAME", "PRG_PLATE", "PRG_ROUTE", "PRG_STAND"}

ents, _ = read_index(os.path.join(ROMFS, "SCRDATA.BIN"))
blob = open(os.path.join(ROMFS, "SCRDATA.ARC"), "rb").read()
SCR = {e["name"].upper(): blob[e["off"]:e["off"] + e["usz"]] for e in ents}
CODE = collections.defaultdict(list)
for off, op, size, ident, ops in ((o for e in ents for o in disasm(blob[e["off"]:e["off"] + e["usz"]])[0])):
    pass


def D(name):
    return disasm(SCR[name.upper()])[0]


# ---- order: DFS over 0x1e calls, from PRG_ROUTE.START ----
order = []
seen = set()


def walk(name):
    key = name.upper()
    if key in seen or key not in SCR:
        return
    seen.add(key)
    order.append(key)
    for off, op, size, ident, ops in D(key):
        if op == 0x1e and ops and ops[0][0] == 3:
            walk(ops[0][1].split(".")[0])


walk("PRG_ROUTE")

DEF = {"1802": "畑中", "0c02": "十萌"}
lines = []
stats = collections.Counter()


def val(ops, i, slots):
    t, v = ops[i]
    if t == 3:
        return v
    if t == 6:
        return slots.get(v, "")
    return ""


def clean(s, slots):
    s = s.replace("\\n", "")
    s = s.replace("@GameLast", slots.get("1802", "畑中"))
    return s


prev = [None, None]          # (op, text)
dbg = [False]                # 当前是否处于 bc0b 调试守卫块内


def debug_skip(res):
    """`0x37 (0400, bc0b, 0)` + `0x22 T` … `0x23 T` ＝ 调试菜单块（bc0b 本体恒 0、仅 DEBUG 置 3）。
    块内是「誰のルートに入っていますか？」「〜回目のミニゲームに成功しましたか？」等开发用跳转/旗设定。"""
    skip = set()
    for i, (off, op, size, ident, ops) in enumerate(res):
        if op == 0x37 and len(ops) == 3 and ops[0] == (2, "0400") and ops[1] == (2, "bc0b") \
                and ops[2] == (1, "00000000"):
            nxt = res[i + 1] if i + 1 < len(res) else None
            if not nxt or nxt[1] != 0x22:
                continue
            tgt = nxt[4][0][1]
            for j in range(i + 1, len(res)):
                if res[j][1] == 0x23 and res[j][4] and res[j][4][0][1] == tgt:
                    skip.update(range(i, j + 1))
                    break
    return skip


def emit(op, s):
    """0x5a 固定名 / 0xfc %s 互斥成对 ⇒ 槽位替换后同文者按 op 型别去重（只认跨型别相邻）。"""
    if s and prev[1] == s and op != prev[0] and "fc" in (op, prev[0]):
        return False
    lines.append(s)
    prev[0], prev[1] = op, s
    return True


for name in order:
    if name in SYSTEM:
        continue
    slots = dict(DEF)
    RES = D(name)
    SKIP = debug_skip(RES)
    for idx, (off, op, size, ident, ops) in enumerate(RES):
        if idx in SKIP:
            continue
        if op in (0xfd, 0x132):
            if len(ops) >= 2 and ops[0][0] == 6:
                tgt = ops[0][1]
                if tgt in ("2402", "3402"):      # 名札窗：丢弃
                    continue
                slots[tgt] = val(ops, 1, slots)
            continue
        if op == 0x5a:
            for seg in [x.rstrip("\u3000") for x in clean(ops[0][1], slots).split("\\c")]:
                if seg and emit("5a", seg):
                    stats["text"] += 1
        elif op == 0xfc:
            fmt = ops[0][1]
            args = [slots.get(v, "") for t, v in ops[1:] if t == 6]
            try:
                s = fmt % tuple(args)
            except TypeError:
                s = fmt
                for a in args:
                    s = s.replace("%s", a, 1)
            for seg in [x.rstrip("\u3000") for x in clean(s, slots).split("\\c")]:
                if seg and emit("fc", seg):
                    stats["text"] += 1
        elif op == 0xf0:
            lines.append(clean(ops[0][1], slots))
            stats["title"] += 1
        elif op == 0x5c:
            n = int.from_bytes(bytes.fromhex(ops[0][1]), 'little')
            for t, v in ops[1:1 + n]:
                txt = slots.get(v, "") if t == 6 else v
                txt = txt.rsplit(",", 1)[0].rstrip()
                lines.append(txt)
                stats["option"] += 1

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8-sig", newline="\n") as f:
    f.write("\n".join(lines) + "\n")
print("scripts", len(order), "excluded", [s for s in order if s in SYSTEM])
print("lines", len(lines), dict(stats))
