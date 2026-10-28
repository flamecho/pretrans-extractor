#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""マーメイドプリズム VML 提取库（ADP 容器 + JIS7 字符串池 + 32bit op 流）。"""
import struct

UND = '\u3014\u672a\u89e3\u6790\u3015'


def find_vml(d):
    """返回 (起点, strTabOff, count) 列表；带字符串可读性校验。"""
    cand = []
    n = len(d)
    for i in range(0, n - 0x20, 4):
        if d[i:i + 4] != b'\x20\x00\x00\x00':
            continue
        T, C = struct.unpack_from('<II', d, i + 0x18)
        if not (0x20 < T < n) or not (1 <= C < 20000):
            continue
        if i + T + 8 * C > n:
            continue
        ok = 0
        bad = 0
        prev = 0
        broken = False
        for k in range(C):
            L, O = struct.unpack_from('<II', d, i + T + 8 * k)
            if L > 3000 or i + O + L > n or O < 8 * C:
                broken = True
                break
            if k and O < prev:
                broken = True
                break
            prev = O
            b = d[i + O:i + O + L]
            try:
                t = bytes([x + 0x80 for x in b]).decode('euc_jp')
            except Exception:
                bad += 1
                continue
            if any('\u3040' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff' for c in t):
                ok += 1
        if broken:
            continue
        if ok >= max(2, C * 0.6) and bad <= C * 0.2:
            cand.append((ok, i, T, C))
    cand.sort(key=lambda x: (-x[0], x[1]))
    # 去重：同一 VML 内起点 4 字节对齐重复命中时保留最优
    out = []
    for ok, i, T, C in cand:
        if any(abs(i - j) < 0x40 for _, j, _, _ in out):
            continue
        out.append((ok, i, T, C))
    out.sort(key=lambda x: x[1])
    return [(i, T, C) for _, i, T, C in out]


def parse_strings(d, s, T, C):
    out = []
    for k in range(C):
        L, O = struct.unpack_from('<II', d, s + T + 8 * k)
        b = d[s + O:s + O + L]
        try:
            out.append(bytes([x + 0x80 for x in b]).decode('euc_jp'))
        except Exception:
            out.append(UND)
    return out


def ops_of(d, s, T):
    i = s + 0x20
    end = s + T
    seq = []
    while i < end - 4:
        w = struct.unpack_from('<I', d, i)[0]
        if w >> 24 == 0xFF:
            seq.append((i - s, w & 0xFFFFFF, struct.unpack_from('<I', d, i + 4)[0]))
        i += 4
    return seq
