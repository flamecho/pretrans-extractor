#!/usr/bin/env python3
"""dk_scpt.py -- SCPT 单条全解析：op 序列 + 池串。usage: dk_scpt.py NAME"""
import sys, struct, re
sys.path.insert(0, 'tools')
from dk_lib import walk, expand

want = sys.argv[1].upper()
for vol, nm, cs, us, fl, seg in walk(['DATA01']):
    if nm.upper() != want:
        continue
    p = expand(seg, us, fl)
    code_len = struct.unpack_from('<I', p, 12)[0]
    pool = p[0x20 + code_len:]
    print('len', len(p), 'code_len', code_len, 'pool', len(pool))
    i = 0x20
    end = 0x20 + code_len
    while i < end - 4:
        op = p[i]
        if op == 0x19:
            print('%04x 19 %s' % (i, p[i:i + 10].hex()))
            i += 10
            continue
        arg = struct.unpack_from('<I', p, i + 1)[0]
        s = ''
        if op in (0x06, 0x0a) and arg < len(pool):
            s = pool[arg:pool.index(b'\x00', arg)].decode('cp932', 'replace')[:40]
        print('%04x %02x %08x %s' % (i, op, arg, s))
        i += 5
    print('tail', p[i:end].hex())
    print('--- pool')
    for m in re.finditer(rb'[^\x00]+', pool):
        print('  %04x %s' % (0x20 + code_len + m.start(), m.group().decode('cp932', 'replace')[:60]))
    break
