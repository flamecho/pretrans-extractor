#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEAR My SUN!! ～ムスコ★育成★狂騒曲～（PS2 / HuneX IKA SEQ, SLPS_258.10）全文本提取。

链路：ISO9660 → DATA/SCRIPT.BIN（HFU2 容器，376 条）→ UFFA+LZSS → IKA SEQ 字节码
指令：`26 <op:u8> 24 <nargs:u8> <operands>`
  字符串记录：`5C <u8 L> <SJIS (L-4)B> 00 00`（L = 记录总长，含 op+len 两字节）
文本命令（全量 5C 记录 100% 由这三条承载）：
  0x3e n=1  名札（独立名字窗）→ 丢弃
  0x3c n=1  台词／地の文（一框＝一次点击；后续 `26 06 24 00` = クリック待ち）
  0x41 n=3  选项（5C 串 + 8 字节参数；连续数条＝同一组，`26 42 24 00` 收尾）
槽位（SJIS）：8189 ♂ / 818a ♀ / 8190 ＄ —— 两个双胞胎儿子与母亲（均可改名）
换行：串内唯一控制码 `@n` = 同框软换行 → 合并
"""
import struct
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arcanafesta_extract import lzs_decode

SLOTS = {'\uff04': '夏見', '\u2642': '雷斗', '\u2640': '風斗'}   # ＄=母(主角) / ♂=雷斗 / ♀=風斗
NAME_OP, SPEECH_OP, CHOICE_OP = 0x3E, 0x3C, 0x41


def hfu2_blocks(d):
    """返回按索引顺序的 (idx, blob)；嵌套 HFU2 递归展开。"""
    if d[:4] != b'HFU2':
        return [(0, d)]
    cnt = struct.unpack_from('<I', d, 4)[0]
    X = struct.unpack_from('<I', d, 8)[0]
    out = []
    for k in range(cnt):
        o, s, s2, h = struct.unpack_from('<IIII', d, 0x10 + k * 16)
        p = X + o
        if p + 16 <= len(d) and d[p:p + 4] == b'UFFA':
            cs, us = struct.unpack_from('<II', d, p + 4)
            blob = lzs_decode(d[p + 16:p + 16 + cs], us)
        else:
            blob = d[p:p + s]
        out.append((k, blob))
    return out


def scan(d):
    """记录驱动扫描：只认自定界的 5C 记录（永不失步）。产出 (off, op, text)。"""
    N = len(d)
    i = 0
    res = []
    while i < N - 8:
        if d[i] == 0x26 and d[i + 2] == 0x24 and d[i + 4] == 0x5C:
            op, n = d[i + 1], d[i + 3]
            ln = d[i + 5]
            if op in (NAME_OP, SPEECH_OP, CHOICE_OP) and 4 <= ln and i + 4 + ln <= N \
                    and d[i + 4 + ln - 2:i + 4 + ln] == b'\x00\x00':
                try:
                    t = d[i + 6:i + 4 + ln - 2].decode('cp932')
                except UnicodeDecodeError:
                    t = None
                if t is not None:
                    res.append((i, op, t))
                    i += 4 + ln
                    if op == CHOICE_OP:      # 选项记录尾部还有 6 字节参数（写入值 u32 + u16）
                        i += 6
                    continue
        i += 1
    return res


def clean(t):
    t = t.replace('@n', '')
    for k, v in SLOTS.items():
        t = t.replace(k, v)
    return t.strip('\u3000') if t.strip('\u3000') else t


def main():
    src, dst = sys.argv[1], sys.argv[2]
    blocks = hfu2_blocks(open(src, 'rb').read())
    lines = []
    stat = {'name': 0, 'speech': 0, 'choice': 0}
    per_file = []
    for idx, blob in blocks:
        recs = scan(blob)
        n_speech = 0
        for off, op, t in recs:
            if op == NAME_OP:
                stat['name'] += 1
                continue
            s = clean(t)
            if not s:
                continue
            if op == CHOICE_OP:
                stat['choice'] += 1
            else:
                stat['speech'] += 1
                n_speech += 1
            lines.append(s)
        per_file.append((idx, len(blob), len(recs), n_speech))
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('blocks=%d  records: name=%d speech=%d choice=%d' % (len(blocks), stat['name'], stat['speech'], stat['choice']))
    print('output lines=%d -> %s' % (len(lines), dst))
    empty = [x for x in per_file if x[2] == 0]
    print('no-record blocks=%d %s' % (len(empty), empty[:8]))


if __name__ == '__main__':
    main()
