#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""英国探偵ミステリア The Crown (PSV) —— Malie exec.dat → 全文本（一次点击 = 一行）。

用法: python mysteria_text.py <exec.dat> <out.txt> [--name エミリー]

排除：
  * 素材/ギャラリー名リスト（背景名・顔差分名・短冊名・アイテム名・「（空き）」等）
    —— idx 9086..10634 与 31809..32785 两段连续区块
  * 系统 UI 串「削除」（存档槽删除按钮）
规范化：原文误用的半角「･」「､」按作者一贯写法还原为全角「・」「、」（详见报告）。
"""
import sys
import mysteria_extract as ME

NAME_DEFAULT = "エミリー"

# 素材/ギャラリー名リスト（0-based 消息序号，含端点）
EXCLUDE_RANGES = [(9086, 10634), (31809, 32785)]
# 系统 UI 串（整行相等即排除）
EXCLUDE_EXACT = {"削除"}
# 半角 → 全角（原文笔误；游戏内同一含义一贯写作全角）
NORMALIZE = {"\uff65": "\u30fb", "\uff64": "\u3001"}


def clean(seg, name):
    o = []
    i = 0
    n = len(seg)
    while i < n:
        c = ord(seg[i])
        if c == 0x07 and i + 1 < n:
            sub = ord(seg[i+1]); i += 2
            if sub == 0x0C:                        # 主人公名宏 07 0C <n> 00
                j = seg.find("\x00", i)
                if j < 0: j = n
                i = j + 1 if j < n else n
                o.append(name)
            elif sub == 0x01:                      # 注音 07 01 <本体> 0A <読み> 00
                j = seg.find("\x00", i); j = n if j < 0 else j
                o.append(seg[i:j].split("\x0a")[0])
                i = j + 1 if j < n else n
            elif sub in (0x07, 0x08):              # 语音名 07 08 <name> 00
                j = seg.find("\x00", i); i = n if j < 0 else j + 1
            # 07 04 停顿 / 07 06 框终结 / 07 09 等 → 丢
            continue
        if c in (0x00, 0x0A):                      # NUL / 软换行 → 合并（丢）
            i += 1; continue
        if 0x01 <= c <= 0x06:
            i += 1 + ME.SKIP_AFTER.get(c, 0); continue
        o.append(seg[i]); i += 1
    t = "".join(o).rstrip()
    for a, b in NORMALIZE.items():
        t = t.replace(a, b)
    return t


def main():
    src, outp = sys.argv[1], sys.argv[2]
    name = NAME_DEFAULT
    if "--name" in sys.argv:
        name = sys.argv[sys.argv.index("--name") + 1]
    d = open(src, "rb").read()
    P = ME.parse_exec(d)
    msgs, gs = ME.walk_script(P)
    lines = []
    for idx, s in msgs:
        if any(a <= idx <= b for a, b in EXCLUDE_RANGES):
            continue
        t = clean(s, name)
        if not t or t in EXCLUDE_EXACT:
            continue
        lines.append(t)
    with open(outp, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    sys.stderr.write("messages=%d  lines=%d\n" % (len(msgs), len(lines)))


if __name__ == "__main__":
    main()
