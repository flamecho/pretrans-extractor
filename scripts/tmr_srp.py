#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TMR-Hiro ADV System `.srp` → 全文本（PC / クレイジー★ラビッツ 実測）

文件结构（238 场景 ＋ 11 个控制表，26,643 条命令全部闭合）：
  +0x00 u32 命令数；每条 u16 长度 ＋ 该长度的字节，**字节要先做高低半字节互换**
  （`b>>4 | b<<4`，即 PacManager 的 FlipBytes —— 这就是「文件里看着像 hex」的原因）。
  命令体 = [u16 type][u16 flags][data]

opcode（实测）：
  t=0 f=0x30  台詞   `話者,本文,音声ID`
  t=0 f=0x00  地の文 本文
  t=0 f=0x20  台詞（无音声）`話者,本文`
  t=0 f=0x41  系统标记（空）
  t=1 f=0x20  场景跳转（`\\x01\\x02<场景名>`，尾部可能带 `,SCENE_JUMP`）
  t=1 f=0x41  **选项**：`\\x00\\x00<条数>` ＋ 每条 ` [0x20][0x64]<选项文本>,<跳转标签>`
  t=1 f=0x10/0x40/0x00  分支标签 / CG_MODE 等流程
  t=2 美术、t=3 音乐音效、t=4 画面、t=5 系统

成行判据（L0）：**一条 t=0 命令 ＝ 一个文本框 ＝ 一行**（与运行时内存里逐条 NUL 结尾的串一一对应）；
框内的 `\\n`（字面反斜杠+n）是排版换行 ⇒ 合并。台詞的名札走独立名字窗 ⇒ 剔除（`--keep-name` 可保留）。

顺序：章节控制器 `10_chapter_01..04` 里的跳转序列就是真实阅读顺序；选项插在其出现位置。

用法：python scripts/tmr_srp.py <srp目录> <out.txt>
"""
import os
import re
import struct
import sys

NAME = {"＄α": "望月", "＄β": "葵"}   # 主角默认名（namu wiki 记载；语音 ID AOI0010001 佐证）

KIND_TEXT, KIND_JUMP, KIND_CHOICE = 0, 1, 2


def flip(bs):
    return bytes((((b >> 4) | (b << 4)) & 0xFF) for b in bs)


def read_cmds(path):
    d = open(path, "rb").read()
    if len(d) < 4:
        return None
    n, = struct.unpack_from("<I", d, 0)
    if n > 200000:
        return None
    q, out = 4, []
    for _ in range(n):
        if q + 2 > len(d):
            return None
        L, = struct.unpack_from("<H", d, q)
        q += 2
        if q + L > len(d):
            return None
        out.append(flip(d[q:q + L]))
        q += L
    if q != len(d):
        return None
    return out


def clean(s):
    s = s.replace("\\n", "").replace("\r", "")
    for k, v in NAME.items():
        s = s.replace(k, v)
    return s.strip()


def text_of(body, fl, keep_name):
    if fl == 0x0000:
        return clean(body.decode("cp932", "replace"))
    if fl in (0x0020, 0x0030):
        s = body.decode("cp932", "replace")
        parts = s.split(",")
        if len(parts) >= 3 and parts[-1] and parts[-1].isascii():
            nm, t = parts[0], ",".join(parts[1:-1])
        elif len(parts) == 2:
            nm, t = parts[0], parts[1]
        else:
            nm, t = "", s
        if keep_name and nm:
            t = nm + "「" + t + "」"
        return clean(t)
    return ""


def choices_of(body):
    """[u16 ?][u8 条数] ＋ 每条 ` [0x20][0x64]<文本>,<标签>`"""
    out = []
    p = 3
    n = body[2] if len(body) > 2 else 0
    while len(out) < n and p + 2 < len(body):
        if body[p] != 0x20 or body[p + 1] != 0x64:
            p += 1
            continue
        p += 2
        q = body.find(b",", p)
        if q < 0:
            break
        out.append(body[p:q].decode("cp932", "replace").strip())
        p = q + 1
        while p < len(body) and body[p] not in (0x20,):
            p += 1
    return out


def jump_target(body):
    s = body.decode("cp932", "replace").lstrip("\x01\x02")
    return s.split(",")[0].strip()


def main():
    src, outp = sys.argv[1], sys.argv[2]
    keep_name = "--keep-name" in sys.argv

    scenes, flows = {}, {}
    for f in sorted(os.listdir(src)):
        cmds = read_cmds(os.path.join(src, f))
        if not cmds:
            continue
        lines, steps = [], []
        for c in cmds:
            if len(c) < 4:
                continue
            t, fl = struct.unpack_from("<HH", c, 0)
            body = c[4:]
            if t == KIND_TEXT:
                s = text_of(body, fl, keep_name)
                if s:
                    lines.append(s)
            elif t == 1 and fl == 0x0020:
                steps.append(("jump", jump_target(body)))
            elif t == 1 and fl == 0x0041:
                for o in choices_of(body):
                    steps.append(("choice", clean(o)))
        scenes[f] = lines
        flows[f] = steps

    used, out = set(), []

    def emit_scene(name):
        if name in used or name not in scenes:
            return
        used.add(name)
        out.extend(scenes[name])

    for head in ("10_opening", "10_chapter_01", "10_chapter_02", "10_chapter_03", "10_chapter_04"):
        for kind, val in flows.get(head, []):
            if kind == "jump":
                emit_scene(val)
            else:
                out.append(val)

    for f in sorted(scenes, key=lambda x: (len(x), x)):
        if f in used or f.startswith(("10_", "20_", "start", "var", "view")):
            continue
        emit_scene(f)

    with open(outp, "w", encoding="utf-8-sig", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")
    print(f"[i] 场景 {len(scenes)}  行 {len(out)}  → {outp}")
    miss = [f for f in scenes if f not in used and not f.startswith(("10_", "20_", "start", "var", "view"))]
    if miss:
        print(f"[!] 未被章节引用、按文件名兜底: {len(miss)} 个")


if __name__ == "__main__":
    main()
