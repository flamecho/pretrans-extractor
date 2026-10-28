#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NScripter NSA (arc.nsa) 解包 —— 赤い砂堕ちる月 PC 版。
条目 = [name(cp932, 变长)][flag BE u16][offset BE u32][stored BE u32][orig BE u32]
flag=0 明文；flag=1/2 压缩（stored < orig）。
闭合校验：index_end + Σstored == filesize（本作精确成立）。
"""
import os, sys, struct

def parse(path):
    d = open(path, 'rb').read()
    n = len(d)
    p, run = 6, 0
    ents = []
    while p + 14 < n:
        q = p
        while q < n and d[q] != 0:
            q += 1
        name = d[p:q].decode('cp932', 'replace')
        if not name or q + 14 > n:
            break
        flag, off, stored, orig = struct.unpack('>HIII', d[q:q + 14])
        if off != run or flag > 2:
            break
        ents.append((name, off, stored, orig, flag))
        run += stored
        p = q + 14
    assert p + run == n, '闭合失败 %x+%d != %d' % (p, run, n)
    return d, p, ents

def main(src, outdir, only=None):
    d, base, ents = parse(src)
    print('[i] 条目 %d  base=0x%x  闭合 %d == %d' % (len(ents), base, base + sum(e[2] for e in ents), len(d)))
    print('[i] flag 分布', {f: sum(1 for e in ents if e[4] == f) for f in set(e[4] for e in ents)})
    os.makedirs(outdir, exist_ok=True)
    hit = 0
    for name, off, stored, orig, flag in ents:
        if only and not name.lower().endswith(tuple(only)):
            continue
        dst = os.path.join(outdir, name.replace('\\', '/'))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        raw = d[base + off: base + off + stored]
        open(dst + ('.cmp' if flag else ''), 'wb').write(raw)
        hit += 1
    print('[i] 写出 %d 个' % hit)

if __name__ == '__main__':
    only = sys.argv[3].split(',') if len(sys.argv) > 3 else None
    main(sys.argv[1], sys.argv[2], only)
