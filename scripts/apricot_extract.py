#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""怪盗アプリコット ポータブル (PSP, Takuyo gss) 全文本提取。

Container : PSP_GAME/USRDIR/SCRDATA.BIN (LSDARC V.100 index, 114 scripts, all isPacked=0)
            PSP_GAME/USRDIR/SCRDATA.ARC (payload)
Script    : "SCR 2.00"  u16 opcode | u8 size | u16 id | operand*
Text ops  : 0x5a message box text          (one click = one box)
            0xfc message box text + %s slots (protagonist name variables)
            0x5c choices (u32 count, "text, FLAG", ...)
Speaker   : 0xfd assigns slot 0x5f8 (name plate) from 0x608 / literal -> dropped (no prefixes)
Slots     : 0x230 = given name (default あんず), 0x23c = surname (default 望月)  [AUTOEXEC/INIT]
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from himehibi_lsdarc import read_index      # noqa: E402
from himehibi_disasm import disasm          # noqa: E402

GAME = os.environ.get("APRICOT_DIR", os.path.join(HERE, "..", "_work_apricot", "PSP_GAME"))
USDIR = os.path.join(GAME, "USRDIR")
OUT = os.environ.get("APRICOT_OUT",
                     os.path.join(HERE, "..", "提取结果", "怪盗アプリコット_全文本.txt"))

NAME_SLOT = {0x0230: "あんず", 0x023C: "望月"}

# AFTER = おまけ（ギャラリー）ボイス再生中の UI 表示のみ／ENDING = 回収エンド一覧メニュー
EXCLUDE_FILES = {"AFTER", "ENDING"}

# OPENING 冒頭「プロローグを飛ばしますか？」＋2 択＝起動時 UI
SKIP_OPS = {("OPENING", 226), ("OPENING", 261)}

# 剧情顺序：プロローグ → 家（朝）→ 予告状 → 各攻略対象 → サイド → エンディング
ORDER = [
    "OPENING", "FADE", "TIME",
    "ANZU", "ANZU00", "ANZU01", "ANZU02", "TARGET",
    "AYASE", "AYASE00", "AYASE00X", "AYASE01", "AYASE01X", "AYASE02", "AYASE02X", "AYASE03",
    "GENKI", "GENKI00", "GENKI01", "GENKI02", "GENKI03",
    "ICHINOSE", "ICHINOSE00", "ICHINOSE01", "ICHINOSE02", "ICHINOSE03",
    "KIRYUU", "KIRYUU00", "KIRYUU01", "KIRYUU02",
    "MATUBARA", "MATUBARA00", "MATUBARA01", "MATUBARA02", "MATUBARA03",
    "MIZUKI", "MIZUKI00", "MIZUKI01", "MIZUKI02",
    "MITURU", "MITURU00", "MITURU00X",
    "SOU", "SOU00", "SOU00X", "SOU01", "SOU01X", "SOU02", "SOU03",
    "SUOU", "SUOU00", "SUOU01", "SUOU02", "SUOU03",
    "YASHIKI", "YASHIKI00", "YASHIKI01", "YASHIKI02", "YASHIKI03", "YASHIKI04",
    "AZAMI", "AZAMI00", "AZAMI01", "AZAMI02",
    "MIRA", "MIRA00", "RYOUKO", "RYOUKO00", "RYOUKO01",
    "SATOU", "SATOU00", "SATOU01", "AOKI", "AOKI00",
    "ED_828", "ED_AYASE", "ED_KAZUYA", "ED_MIZUKI", "ED_PEOPLE", "ED_RYOUKO",
    "ED_SOU", "ED_THIEF",
    "ED1_AYASE", "ED1_GENKI", "ED1_ICHINOSE", "ED1_KIRYUU", "ED1_MATUBARA",
    "ED1_SOU", "ED1_SUOU", "ED1_YASHIKI",
    "ED2_AYASE", "ED2_GENKI", "ED2_ICHINOSE", "ED2_KIRYUU", "ED2_MATUBARA",
    "ED2_SOU", "ED2_SUOU", "ED2_YASHIKI",
]

CLEAN_C = re.compile(r"\\c#[^#]*#")
CLEAN_X = re.compile(r"\\[a-zA-Z]")


def load():
    ents, _ = read_index(os.path.join(USDIR, "SCRDATA.BIN"))
    data = open(os.path.join(USDIR, "SCRDATA.ARC"), "rb").read()
    scripts, index = {}, []
    for e in ents:
        name = e["name"].upper()
        scripts[name] = disasm(data[e["off"]:e["off"] + e["sz"]])[0]
        index.append(name)
    return scripts, index


def sections(ops):
    secs, cur = [], ("__head__", [])
    for x in ops:
        if x[1] == 0x1A and x[4] and x[4][0][0] == 3:
            secs.append(cur)
            cur = (x[4][0][1], [])
        cur[1].append(x)
    secs.append(cur)
    return secs


def choice_text(o):
    """'表示テキスト, FLAG' -> 表示テキスト（FLAG 側は ASCII のみ）"""
    if "," in o:
        head, tail = o.rsplit(",", 1)
        if tail and all(ord(c) < 0x80 for c in tail):
            return head
    return o


def clean(s, slots):
    s = CLEAN_C.sub("", s)
    if "%s" in s and slots:
        parts = s.split("%s")
        out = parts[0]
        for i, p in enumerate(parts[1:]):
            key = slots[i] if i < len(slots) else None
            out += (NAME_SLOT.get(key, "") if key is not None else "") + p
        s = out
    s = CLEAN_X.sub("", s)
    return s.strip()


def main():
    scripts, index = load()
    SEC = {n: sections(o) for n, o in scripts.items()}
    byname = {n: dict(s) for n, s in SEC.items()}
    byteorder = {n: [lbl for lbl, _ in s] for n, s in SEC.items()}

    visit_order = {}       # file -> [labels] first-visit order (call graph)
    seen = set()

    def walk(name, label, depth=0):
        if depth > 40 or (name, label) in seen:
            return
        ops = byname.get(name, {}).get(label)
        if ops is None:
            return
        seen.add((name, label))
        visit_order.setdefault(name, []).append(label)
        for x in ops:
            if x[1] in (0x1E, 0x1D) and len(x[4]) >= 2 and x[4][0][0] == 3 and x[4][1][0] == 3:
                walk(x[4][0][1].upper().replace(".SCR", ""), x[4][1][1], depth + 1)

    # 全ファイル：呼出順（あれば）／なければバイト順で節を走査
    for n in ORDER + index:
        for lbl in byteorder.get(n, []):
            walk(n, lbl)

    def labels_for(n):
        order = list(visit_order.get(n, []))
        for lbl in byteorder.get(n, []):
            if lbl not in order:
                order.append(lbl)
        return order

    files = [n for n in ORDER if n in scripts]
    files += [n for n in index if n not in files]

    lines, ntext, nchoice = [], 0, 0
    dbg = os.environ.get("APRICOT_DEBUG")
    for n in files:
        if n in EXCLUDE_FILES:
            continue
        if dbg:
            has = any(any(x[1] in (0x5A, 0xFC, 0x5C) for x in byname[n].get(l, []))
                      for l in labels_for(n))
            if has:
                print(f"FILE {n} start={len(lines)}")
        for lbl in labels_for(n):
            for x in byname[n].get(lbl, []):
                if (n, x[0]) in SKIP_OPS:
                    continue
                op, args = x[1], x[4]
                if op in (0x5A, 0xFC):
                    s = [v for k, v in args if k == 3]
                    if not s:
                        continue
                    slots = ([int.from_bytes(bytes.fromhex(v), "little")
                              for k, v in args[1:] if k == 6] if op == 0xFC else [])
                    t = clean(s[0], slots)
                    if t:
                        lines.append(t)
                        ntext += 1
                elif op == 0x5C:
                    for o in [v for k, v in args if k == 3]:
                        t = clean(choice_text(o), [])
                        if t:
                            lines.append(t)
                            nchoice += 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"files={len(files)} text={ntext} choice={nchoice} lines={len(lines)}")
    print("OUT", os.path.normpath(OUT))


if __name__ == "__main__":
    main()
