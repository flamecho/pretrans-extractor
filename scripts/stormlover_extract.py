#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""STORM LOVER V (PSV PCSG00735) sc.cpk 正文提取（2026-10-11）。

自建字符集见 stormlover_charset.py（cp932 原序，剔 0x81FC/Greek/Cyrillic/0x849F，0 偏移）。

命令结构（≥0xFF00，实测）：
  fff0 <style> <NAME>   说话人名字段（输出丢弃）
  ffff       <BODY>     正文框开始（= 一次点击）
  fffe       <TEXT>     框内换行（合并）
  fffb                  消息分隔
  其它命令(ff33/ff32/ff68/fee6/ffe5/ff03/ffec/ff71/...) 其后 1-2 word 为参数，非正文。
策略：**只取 fff0/ffff/fffe 之后的文本**；其余命令视为分隔。
"""
import os, sys, struct

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stormlover_charset import CHARSET

C_NAME = 0xFFF0
C_BOX = 0xFFFF
C_BR = 0xFFFE
C_SEP = 0xFFFB
TEXT_CMDS = {C_NAME, C_BOX, C_BR}


def tokenize(d):
    """u16 流 → [(cmd, text), ...]；cmd 为最近的命令码（0=文件头前的裸文本，丢弃）。"""
    n = len(CHARSET)
    N = len(d) // 2
    vals = struct.unpack_from('<%dH' % N, d, 0)
    out = []
    cur = 0
    buf = []
    for v in vals:
        if v >= 0xFF00:
            out.append((cur, ''.join(buf)))
            buf = []
            cur = v if v in TEXT_CMDS else -1   # -1 = 非文本命令
            continue
        if cur in (0, -1):
            buf = []                            # 头部裸文本/命令参数：不收集
            continue
        buf.append(CHARSET[v] if 0 <= v < n else '')
    out.append((cur, ''.join(buf)))
    return out


def split_boxes(toks):
    """→ [box_lines, ...]；box_lines = [line1, line2, ...]（框内换行）"""
    boxes = []
    cur = None
    for cmd, text in toks:
        if cmd == C_BOX:
            if cur is not None:
                boxes.append(cur)
            cur = [text]
        elif cmd == C_BR:
            if cur is not None:
                cur.append(text)
        elif cmd == C_NAME:
            continue
        else:                                   # 非文本命令 / 头部
            if cur is not None:
                boxes.append(cur)
                cur = None
    if cur is not None:
        boxes.append(cur)
    return boxes


def merge_box(lines):
    if not lines:
        return ''
    head = lines[0]
    tail = ''.join(x.lstrip('\u3000') for x in lines[1:])
    return (head + tail).strip('\x00')


def extract_text(d):
    """→ 本 entry 的全部正文行（一框一行，框内换行合并）。"""
    return [merge_box(b) for b in split_boxes(tokenize(d))]


def main():
    from cpk import CPK
    c = CPK(sys.argv[1])
    names = sys.argv[2:] if len(sys.argv) > 2 else None
    for e in c.entries:
        if names and e['name'] not in names:
            continue
        d = c.raw(e)
        print('===== %s (%d B) =====' % (e['name'], len(d)))
        for ln in extract_text(d)[:50]:
            if ln:
                print('  ' + ln[:170])
        print()


if __name__ == '__main__':
    main()
