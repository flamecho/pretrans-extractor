# -*- coding: utf-8 -*-
"""按 [op][0x13a][id][0x10] 三元组重建 STCM2L 指令流"""
import struct

U = lambda d, o: struct.unpack_from('<I', d, o)[0]


def stream(d):
    """返回 [(pos, op, id, text|None)]，按文件偏移"""
    out = []
    n = len(d)
    for p in range(4, n - 12):
        if d[p:p + 4] != b'\x3a\x01\x00\x00':
            continue
        if U(d, p + 8) != 0x10:
            continue
        out.append((p, U(d, p - 4), U(d, p + 4), text_at(d, p + 12)))
    return out


def text_at(d, t):
    if t + 16 > len(d):
        return None
    if U(d, t) != 0 or U(d, t + 8) != 1:
        return None
    L = U(d, t + 12)
    if L < 4 or L > 16384 or L & 3:
        return None
    raw = d[t + 16:t + 16 + L].rstrip(b'\x00')
    if (len(raw) + 1 + 3) // 4 * 4 != L:
        return None
    try:
        s = raw.decode('utf-8')
    except UnicodeDecodeError:
        return None
    if '\x00' in s:
        return None
    return s
