#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""怪盗アプリコット 外伝 満編（PC / Takuyo GSS, SCRDATA = LSDARC V.100 + SCR 1.10）

链路：
  APRICOT_SP.ISO（ISO9660，7z 头部报错 ⇒ 用本目录 iso_lite 思路自读）
   → SCRDATA.BIN（索引）+ SCRDATA.ARC（LSD\1a 打包）
   → gss_lsdarc.unpack_entry → 每脚本 "SCR 1.10" 字节码
   → 记录 `[u8 op][u16 BE total_len][u16 LE cmd_id][typed args]`
       typed arg: 0x01 = int32 / 0x02 = u16 var / 0x03 = NUL 结尾 cp932 串
   → op 0x5a = 正文（一框 = 一次点击）

用法：python scripts/apricot_gaiden_extract.py [--src DIR] [--out FILE]
"""
import argparse
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gss_lsdarc as L  # noqa: E402

SRC = r"_work_apricot_gaiden/iso"
OUT = r"提取结果/[PC-JP]怪盗アプリコット 外伝 満編.txt"

# 场转点/竖排特效等控制码（GSS 文本内嵌）
CC = re.compile(r"\\[a-z@#][^\s]")


def records(data):
    o = 0x10
    while o + 3 <= len(data):
        op = data[o]
        ln = (data[o + 1] << 8) | data[o + 2]
        if ln < 3 or o + ln > len(data):
            raise ValueError("bad record at 0x%x op=%02x len=%d" % (o, op, ln))
        yield o, op, data[o + 3:o + ln]
        o += ln


def first_string(pay):
    if len(pay) < 4 or pay[2] != 3:
        return None
    i = pay.find(b"\x00", 3)
    return pay[3:i]


def clean(raw):
    """一框文本 → 一行：去 `\\n　\\n\\d` 尾缀（框尾待ち），框内软换行合并。"""
    t = raw.decode("cp932")
    t = re.sub(r"(?:\\n\u3000)*\\n\\d$", "", t)
    t = t.replace("\\n", "")
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=SRC)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()

    ents, arc = L.load(os.path.join(a.src, "SCRDATA.BIN"),
                       os.path.join(a.src, "SCRDATA.ARC"))
    order = ["WAKA"]  # 唯一含剧情的脚本，线性单节
    lines = []
    for name in order:
        e = next(x for x in ents if x["name"] == name)
        data = L.unpack_entry(arc, e)
        assert data[:8] == b"SCR 1.10", data[:8]
        for o, op, pay in records(data):
            if op != 0x5A:
                continue
            s = first_string(pay)
            if s is None:
                continue
            t = clean(s)
            if t:
                lines.append(t)
    out = "\n".join(lines) + "\n"
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write(out)
    print("%s  %d lines" % (a.out, len(lines)))


if __name__ == "__main__":
    main()
