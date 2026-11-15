# -*- coding: utf-8 -*-
"""LoverPretend STCM2L 节点链行走器

节点 = [1][tag][arg][size][payload...]，size 在 +0x0C，含整个节点
文本节点: payload = [ptr==q+0x2C][2.0f][2.0f][KIND][0x13a][id][0x10][0][L/4][1][L][text]
命令节点: payload = [opcode][0x13a][id][0x10][...]
"""
import struct

U = lambda d, o: struct.unpack_from('<I', d, o)[0]


def walk(d, start, end=None):
    N = len(d) if end is None else end
    q = start
    out = []
    while q + 0x10 <= N:
        sz = U(d, q + 0x0C)
        if sz < 12 or sz > 65536 or q + sz > N:
            break
        if U(d, q + 0x10) == q + 0x2C and sz >= 0x3C:
            L = U(d, q + 0x38)
            if sz == 60 + L and L >= 4 and L <= 16384 and not L & 3:
                raw = d[q + 0x3C:q + 0x3C + L].rstrip(b'\x00')
                try:
                    s = raw.decode('utf-8')
                    ok = True
                except UnicodeDecodeError:
                    s = ''
                    ok = False
                out.append(('T', q, sz, U(d, q + 0x1C), U(d, q + 0x24), s, ok))
                q += sz
                continue
        out.append(('C', q, sz, U(d, q + 0x10), U(d, q + 0x24), '', True))
        q += sz
    return out, q


def find_start(d):
    """从最早一个「文本节点」往前回溯到链首"""
    N = len(d)
    first = None
    for q in range(0, N - 0x3C):
        if U(d, q + 0x10) != q + 0x2C:
            continue
        L = U(d, q + 0x38)
        if L < 4 or L > 16384 or L & 3:
            continue
        if U(d, q + 0x0C) != 60 + L:
            continue
        if U(d, q + 0x2C) != 0 or U(d, q + 0x30) != L // 4 or U(d, q + 0x34) != 1:
            continue
        first = q
        break
    if first is None:
        return 0xa50
    cur = first
    for _ in range(100000):
        found = None
        for cand in range(max(0, cur - 200), cur):
            sz = U(d, cand + 0x0C)
            if cand + sz == cur and 12 <= sz <= 20000:
                found = cand
                break
        if found is None:
            break
        cur = found
    return cur
