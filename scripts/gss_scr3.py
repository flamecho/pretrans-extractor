#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SCR 3.00 (Takuyo gss / Switch) disassembler.
instr: op u16, size u16 (total bytes incl. 6-byte header), id u16, operands <u8 type><data>
"""
import struct

SIZES = {0x00: 1, 0x01: 4, 0x02: 2, 0x03: None, 0x04: 2, 0x05: 4, 0x06: 2, 0x07: 2, 0x08: 2}

def disasm(b, start=16):
    i, n = start, len(b)
    out = []
    while i + 6 <= n:
        op = struct.unpack_from('<H', b, i)[0]
        size = struct.unpack_from('<H', b, i + 2)[0]
        if size < 6 or i + size > n:
            return out, (i, 'sizebad', size)
        ident = struct.unpack_from('<H', b, i + 4)[0]
        p = i + 6
        ops = []
        ok = True
        while p < i + size:
            t = b[p]; p += 1
            if t == 0x03:
                e = b.find(b'\x00', p, i + size + 1)
                if e < 0 or e > i + size:
                    return out, (i, 'str', t)
                ops.append((3, b[p:e].decode('cp932', 'replace'))); p = e + 1
            else:
                sz = SIZES.get(t)
                if sz is None:
                    return out, (i, 'type%#x' % t, t)
                if p + sz > i + size:
                    return out, (i, 'ovf', t)
                ops.append((t, b[p:p + sz].hex())); p += sz
        if p != i + size:
            return out, (i, 'misalign', (p - i, size))
        out.append((i, op, size, ident, ops))
        i += size
    return out, None

if __name__ == '__main__':
    import sys, os, collections
    root = sys.argv[1] if len(sys.argv) > 1 else 'scr_all'
    total = ok = 0
    opcount = collections.Counter()
    opstr = collections.defaultdict(collections.Counter)
    errs = collections.Counter()
    for fn in sorted(os.listdir(root)):
        b = open(os.path.join(root, fn), 'rb').read()
        res, err = disasm(b)
        total += 1
        if err is None: ok += 1
        else: errs[err[1:]] += 1
        for off, op, size, ident, ops in res:
            opcount[op] += 1
            ns = sum(1 for t, v in ops if t == 3)
            if ns: opstr[op][ns] += 1
    print('files ok=%d/%d' % (ok, total))
    print('errors:', errs.most_common(8))
    print('top opcodes:')
    for op, c in opcount.most_common(40):
        print('  op=%#06x count=%d str_pats=%s' % (op, c, dict(opstr[op])))
