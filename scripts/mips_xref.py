#!/usr/bin/env python3
"""mips_xref.py — 线性扫描 + lui/addiu 地址恢复（PS2 R5900）。"""
import struct
import sys

from capstone import *

d = open(sys.argv[1], 'rb').read()
base = int(sys.argv[2], 0)
off = int(sys.argv[3], 0)
size = int(sys.argv[4], 0)
code = d[off:off + size]
md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 + CS_MODE_LITTLE_ENDIAN)

ins_list = []
p = 0
while p < len(code):
    got = list(md.disasm(code[p:p + 4], base + p))
    if got:
        ins_list.append(got[0])
    p += 4
print('insns', len(ins_list))

# lui value tracking per register
targets = {}
last_lui = {}
for ins in ins_list:
    m, ops = ins.mnemonic, ins.op_str.replace(' ', '')
    if m == 'lui':
        parts = ops.split(',')
        try:
            last_lui[parts[0]] = (int(parts[1], 0), ins.address)
        except Exception:
            pass
    elif m in ('addiu', 'ori', 'addi'):
        parts = ops.split(',')
        dst, src = parts[0], parts[1]
        hi = last_lui.get(src)
        if not hi or ins.address - hi[1] > 16:
            continue
        try:
            lo = int(parts[2], 0)
        except Exception:
            continue
        if m == 'ori':
            val = (hi[0] << 16) | (lo & 0xffff)
        else:
            val = ((hi[0] << 16) + (lo if lo < 0x8000 else lo - 0x10000)) & 0xffffffff
        targets.setdefault(val, []).append(ins.address)

print('addrs', len(targets))
if len(sys.argv) > 5:
    for w in sys.argv[5:]:
        w = int(w, 0)
        print(hex(w), [hex(x) for x in targets.get(w, [])])
else:
    for k in sorted(targets):
        if 0x240000 <= k <= 0x280000:
            print(hex(k), [hex(x) for x in targets[k]])
