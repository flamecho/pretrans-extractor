#!/usr/bin/env python3
"""スキップ・ビート！(PS2, SLPM_551.70) シナリオ抽出。

引擎：SCENE00.AFS（CRI AFS）内 77 个场景块，块内为自研字节码：
  - 消息记录： u32 0x00000E18 | u16 flags | u16 f2 | u16 text_off | u16 seq | ...
              text_off 指向块内 cp932 字符串池（NUL 结尾）
  - 选项块：   1B 28 | u16 count | 06 81 01 00 | count × 8B{ u16 str, u16 0x0001,
              u16 idx, u16 0xFF00 } | 22 02
  - 字符串尾部控制码：%K=改行 %P=クリック待ち %N=枠内改行 %FS/%FE=字号 %C*=%色
一行 = 一条消息记录（%K%P 收尾），同记录内 %N 为框内软换行 ⇒ 合并。
"""
import os
import re
import struct
import sys

SCENE_DIR = r"_work_skipbeat/scene"
OUT = r"提取结果/[PS2-JP]スキップ・ビート！.txt"

MSG_SIG = b"\x18\x0e\x00\x00"
CAP = re.compile(r"【[^】]{1,20}】")


def is_jp(s):
    return re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", s)


def clean(s):
    s = re.sub(r"(%[A-Z0-9]+)+$", "", s)          # 尾部控制码
    s = re.sub(r"%C[0-9A-F]{5,6}", "", s)          # 颜色
    s = s.replace("%FS", "").replace("%FE", "")    # 字号
    s = s.replace("%LC", "").replace("%LE", "").replace("%CE", "")
    s = s.replace("%N", "")                        # 框内改行 ⇒ 合并
    s = s.replace("%K", "").replace("%P", "")
    s = s.replace("⑳", "蓮")                       # 名字槽：⑳=蓮（敦賀蓮）
    s = re.sub(r"[\u3000 ]{2,}", "", s)            # 字下げ（连続全角空格）
    s = s.strip(" \u3000")
    m = re.match(r"^【[^】]{1,20}】", s)
    if m:
        s = s[m.end():].strip(" \u3000")
    return s


def messages(d):
    out = []
    o = 0
    while True:
        o = d.find(MSG_SIG, o)
        if o < 0:
            break
        f = struct.unpack_from("<6H", d, o)
        p = f[3]
        if 0x20 <= p < len(d) and f[4] != 0xFFFF:   # seq=0xFFFF ⇒ 控制码记录，非新框
            e = d.find(b"\x00", p)
            if e > p:
                raw = d[p:e]
                try:
                    s = raw.decode("cp932")
                except UnicodeDecodeError:
                    s = None
                if s and s.strip() and not re.fullmatch(r"(%[A-Z0-9]+)+", s):
                    out.append((o, "msg", s))
        o += 4
    return out


def options(d):
    out = []
    o = 0
    while True:
        o = d.find(b"\x1b\x28", o)
        if o < 0:
            break
        n = struct.unpack_from("<H", d, o + 2)[0]
        if (2 <= n <= 8 and d[o + 4:o + 6] == b"\x06\x81"
                and d[o + 8 + n * 8:o + 10 + n * 8] == b"\x22\x02"):
            for i in range(n):
                q = o + 8 + i * 8
                p = struct.unpack_from("<H", d, q)[0]
                if 0x20 <= p < len(d):
                    e = d.find(b"\x00", p)
                    try:
                        s = d[p:e].decode("cp932")
                    except UnicodeDecodeError:
                        s = None
                    if s and is_jp(s):
                        out.append((q, "opt", s))
            o += 8 + n * 8
        o += 2
    return out


def main():
    rows = []
    stats = []
    for i in range(0, 77):
        p = os.path.join(SCENE_DIR, "SCENE00_%03d.bin" % i)
        if not os.path.exists(p):
            continue
        d = open(p, "rb").read()
        ms = messages(d)
        if not ms:
            continue
        ev = ms + options(d)
        ev.sort(key=lambda x: x[0])
        stats.append((i, len(ms), sum(1 for e in ev if e[1] == "opt")))
        for off, kind, s in ev:
            t = clean(s)
            if t:
                rows.append(t)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("\n".join(rows) + "\n")
    print("files", len(stats), "lines", len(rows))
    print("msgs", sum(s[1] for s in stats), "opts", sum(s[2] for s in stats))


if __name__ == "__main__":
    main()
