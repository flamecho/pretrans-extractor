#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ひめひび 続！二学期 —— 第 2 段：eboot 串表抽取 + 成品组装。

第 1 段（对话正文）由 himehibi2_extract.py 产出。
本脚本从 eboot（SELF→ELF 转出）抽取日文串表，剔除：
  · 他作（另一款 Takuyo 作品）遗留场景菜单串（红霞市/神楽坂響/… 连续区块）
  · 名字输入用的标点字库行（夹在两条锚点之间）
  · 场景标题列表（与脚本内 0xf0 标题卡重复）
  · `error : psvita_saveload` 内部日志
并把【人物紹介】(角色图鉴) 与【システム・ヘルプ】(UI/帮助) 并入成品末尾。

Usage:
  python himehibi2_eboot.py <eboot.elf> <dialogue.txt> <out.txt>
"""
import io
import sys

# 他作遗留串连续区块的定位锚点
LEFTOVER_START = "紅霞市案内"
LEFTOVER_MARK = ["ルゥト", "花柳街"]
# 场景标题区间（与 0xf0 标题卡重复 → 剔除）首尾锚点
TITLE_FIRST = "始業式の放課後"
TITLE_LAST = "眩しい日射しに誘われて……"
# 角色图鉴区间首尾锚点
PROFILE_FIRST = "名前は……言うまでもないよね。"
PROFILE_LAST = "トリオ・ザ・ファンクラブ～"
# 名字输入标点字库：夹在这两条锚点之间，无条件剔除
CHARSET_ANCHOR_A = "ここからやり直しますか？"
CHARSET_ANCHOR_B = "システムセーブを行いますか？"


def _jp_ok(s):
    if len(s) < 2:
        return False
    if not any(("\u3040" <= c <= "\u30ff") or ("\u4e00" <= c <= "\u9fff")
               or ("\uff00" <= c <= "\uffef") or ("\u3000" <= c <= "\u303f") for c in s):
        return False
    for c in s:
        o = ord(c)
        if o < 0x20 or 0xE000 <= o <= 0xF8FF or o > 0xFFFF:
            return False
    return True


def eboot_lines(elf_path):
    d = open(elf_path, "rb").read()
    out, seen = [], set()
    for chunk in d.split(b"\x00"):
        if len(chunk) < 2:
            continue
        for part in chunk.replace(b"\x0d", b"\n").split(b"\n"):
            if len(part) < 2:
                continue
            try:
                s = part.decode("utf-8").strip()
            except UnicodeDecodeError:
                continue
            if _jp_ok(s) and s not in seen:
                seen.add(s)
                out.append(s)
    return out


def build(elf_path, dialogue_path, out_path):
    ss = eboot_lines(elf_path)

    lo = next(i for i, s in enumerate(ss) if LEFTOVER_START in s)
    hi = max(i for i, s in enumerate(ss) if any(m in s for m in LEFTOVER_MARK))
    t_start = ss.index(TITLE_FIRST)
    t_end = ss.index(TITLE_LAST) + 1
    p_start = ss.index(PROFILE_FIRST)
    p_end = ss.index(PROFILE_LAST) + 1
    cs_a = ss.index(CHARSET_ANCHOR_A)
    cs_b = ss.index(CHARSET_ANCHOR_B)

    profiles = ss[p_start:p_end]
    system, seen = [], set(profiles)
    for i, s in enumerate(ss):
        if not s or s in seen:
            continue
        if lo <= i <= hi or t_start <= i < t_end or p_start <= i < p_end:
            continue
        if cs_a < i < cs_b:
            continue
        if s.startswith("error :"):
            continue
        seen.add(s)
        system.append(s)

    dial = io.open(dialogue_path, encoding="utf-8-sig").read().split("\n")
    if dial and dial[-1] == "":
        dial.pop()

    lines = list(dial) + ["", "【人物紹介】"] + profiles + ["", "【システム・ヘルプ】"] + system
    with io.open(out_path, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    sys.stderr.write(f"dialogue={len(dial)} profiles={len(profiles)} "
                     f"system={len(system)} total={len(lines)}\n")
    sys.stderr.write("wrote " + out_path + "\n")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2], sys.argv[3])
