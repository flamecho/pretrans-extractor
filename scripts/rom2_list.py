#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ROM2 目录列表 / 按名提取（不整文件入内存）"""
import struct, os, sys
from collections import deque


def u32(f, o):
    f.seek(o)
    return struct.unpack('<I', f.read(4))[0]


def parse_blocks(f, N):
    pos = 0x20
    blocks = []
    while pos + 4 <= N:
        cnt = u32(f, pos)
        if cnt == 0 or cnt > 20000:
            break
        entries = []
        me = 0
        bad = False
        for i in range(cnt):
            eo = pos + 4 + i * 12
            if eo + 12 > N:
                bad = True
                break
            f0 = u32(f, eo)
            f1 = u32(f, eo + 4)
            f2 = u32(f, eo + 8)
            o = pos + (f0 & 0x7fffffff)
            f.seek(o)
            nm = b''
            while True:
                c = f.read(1)
                if not c or c == b'\0':
                    break
                nm += c
            entries.append((nm.decode('latin1'), bool(f0 >> 31), f1, f2))
            me = max(me, o + len(nm) + 1)
        if bad or not entries:
            break
        blocks.append((pos, entries))
        pos = (me + 15) & ~15
    return blocks


def build_tree(blocks):
    res = {0: ''}
    q = deque()
    for (nm, isd, f1, f2) in blocks[0][1]:
        if isd and nm not in ('.', '..'):
            q.append((nm, ''))
    idx = 1
    while q and idx < len(blocks):
        nm, parent = q.popleft()
        p = parent + '/' + nm
        res[idx] = p
        for (cn, cd, cf1, cf2) in blocks[idx][1]:
            if cd and cn not in ('.', '..'):
                q.append((cn, p))
        idx += 1
    return res


def main():
    src = sys.argv[1]
    f = open(src, 'rb')
    f.seek(0, 2)
    N = f.tell()
    unit = u32(f, 0x0c) or 0x200
    blocks = parse_blocks(f, N)
    res = build_tree(blocks)
    print('blocks=%d unit=0x%x size=%d' % (len(blocks), unit, N))
    mode = sys.argv[2] if len(sys.argv) > 2 else 'list'
    outdir = sys.argv[3] if len(sys.argv) > 3 else '_w_um/rom'
    want = sys.argv[4].lower() if len(sys.argv) > 4 else None
    tot = 0
    for bi, (bpos, entries) in enumerate(blocks):
        base = res.get(bi, '/?')
        for (nm, isd, f1, f2) in entries:
            if nm in ('.', '..') or isd:
                continue
            p = (base + '/' + nm)
            tot += 1
            if mode == 'list':
                print('%-70s %12d' % (p, f2))
            else:
                if want and want not in p.lower():
                    continue
                op = os.path.join(outdir, p.lstrip('/'))
                os.makedirs(os.path.dirname(op), exist_ok=True)
                f.seek(f1 * unit)
                left = f2
                with open(op, 'wb') as w:
                    while left:
                        b = f.read(min(1 << 22, left))
                        if not b:
                            break
                        w.write(b)
                        left -= len(b)
    if mode == 'list':
        print('files', tot)


if __name__ == '__main__':
    main()
