#!/usr/bin/env python3
"""dk_trace.py -- 逐指令 trace（把 0x19 的 a/b 与 06 的串名解析出来）。usage: dk_trace.py NAME [skip] [n]"""
import sys, struct
sys.path.insert(0, 'tools')
from dk_lib import walk, expand

want = sys.argv[1].upper()
skip = int(sys.argv[2]) if len(sys.argv) > 2 else 0
lim = int(sys.argv[3]) if len(sys.argv) > 3 else 90
for vol, nm, cs, us, fl, seg in walk(['DATA01']):
    if nm.upper() != want:
        continue
    p = expand(seg, us, fl)
    cl = struct.unpack_from('<I', p, 12)[0]
    i, end, k = 0x20, 0x20 + cl, 0
    while i < end - 4:
        op = p[i]
        if op == 0x19:
            a, b = p[i + 1], p[i + 2]
            desc = '19 a=%02x b=%02x' % (a, b)
            ln = 10
        else:
            arg = struct.unpack_from('<I', p, i + 1)[0]
            desc = '%02x %08x' % (op, arg)
            if op in (0x06, 0x0a, 0x0b, 0x0c, 0x0d) and 0 < arg < len(p):
                e = p.find(b'\x00', arg)
                desc += ' "' + p[arg:e][:36].decode('cp932', 'replace').replace('\n', '\\n') + '"'
            ln = 5
        if k >= skip:
            print('%04x %s' % (i, desc))
        k += 1
        if k >= skip + lim:
            break
        i += ln
    break
