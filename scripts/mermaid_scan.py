#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""マーメイドプリズム (PS2, SLPS_256.96) — ADVIMG.ADP 内 VML 走查/统计。

ADP: [u32 count][u32 hdr=16][u32 dataStart] + count * 0x30 条目
     条目 = [u32 off][u32 cnt][u32 size][u32 cnt*48][u8 flag][name 31B]
VML: 头 0x20 = [0x20][?][?][1][?][1][strTabOff][strCount]
     代码 4 字节对齐，op = u32 (高字节 0xFF)，op&0xFFFFFF
     字符串表 strTabOff: strCount * [u32 len][u32 off]，文本 = JIS7 (b+0x80 -> euc_jp)
"""
import struct, sys, os

ISO = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '_iso', 'Mermaid Prism (Japan).iso')
ADP_LBA = 1120


def adp_entries(f):
    f.seek(ADP_LBA * 2048)
    h = f.read(0x6800)
    n = struct.unpack_from('<I', h, 0)[0]
    out = []
    for k in range(n):
        st = 0x10 + k * 0x30
        off, cnt, size, idxsize = struct.unpack_from('<IIII', h, st)
        flag = h[st + 0x10]
        nm = h[st + 0x11:st + 0x11 + 31].split(b'\0')[0].decode('latin1')
        out.append(dict(name=nm, off=off, size=size, cnt=cnt, idx=idxsize, flag=flag))
    out.sort(key=lambda e: e['off'])
    for i, e in enumerate(out):
        end = out[i + 1]['off'] if i + 1 < len(out) else e['off'] + e['size']
        e['span'] = max(e['size'], end - e['off'])
    return out


def find_vml(d):
    """返回 VML 起点列表（strTabOff/strCount 自洽）。"""
    res = []
    n = len(d)
    for i in range(0, n - 0x20, 4):
        if d[i] != 0x20 or d[i + 1] or d[i + 2] or d[i + 3]:
            continue
        T, C = struct.unpack_from('<II', d, i + 0x18)
        if not (0x20 < T < n) or not (0 < C < 20000):
            continue
        if i + T + 8 * C > n:
            continue
        ok = True
        prev = 0
        for k in range(min(C, 16)):
            L, O = struct.unpack_from('<II', d, i + T + 8 * k)
            if O < 8 * C or i + O + L > n or L > 2000:
                ok = False
                break
            if k and O < prev:
                ok = False
                break
            prev = O
        if ok:
            res.append(i)
    return res


def parse_vml(d, s):
    T, C = struct.unpack_from('<II', d, s + 0x18)
    strs = []
    for k in range(C):
        L, O = struct.unpack_from('<II', d, s + T + 8 * k)
        b = d[s + O:s + O + L]
        try:
            strs.append(bytes([x + 0x80 for x in b]).decode('euc_jp'))
        except Exception:
            strs.append('\u3014\u672a\u89e3\u6790\u3015')
    return strs, T


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


if __name__ == '__main__':
    f = open(ISO, 'rb')
    ent = adp_entries(f)
    import collections
    hist = collections.Counter()
    nv = 0
    nmiss = []
    for e in ent:
        if not (e['name'].startswith('S') and e['name'][1:].isdigit()):
            continue
        f.seek(e['off'])
        d = f.read(e['size'])
        vs = find_vml(d)
        if not vs:
            nmiss.append(e['name'])
            continue
        nv += 1
        for s in vs:
            strs, T = parse_vml(d, s)
            for p, op, a in ops_of(d, s, T):
                hist[op] += 1
    print('S entries:', sum(1 for e in ent if e['name'].startswith('S') and e['name'][1:].isdigit()))
    print('with VML:', nv, 'miss:', len(nmiss), nmiss[:20])
    print('top ops:', [(hex(k), v) for k, v in hist.most_common(40)])
