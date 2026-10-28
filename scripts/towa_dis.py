# -*- coding: utf-8 -*-
"""悠久ノ桜 SLPM_668.45 最小反汇编：ELF32 MIPS(LE) → .text 反汇编落盘 + 立即数索引。"""
import struct, sys, os
from capstone import *

ELF = "_work_towa/SLPM_668.45"
d = open(ELF, 'rb').read()
assert d[:4] == b'\x7fELF'
e_shoff = struct.unpack_from('<I', d, 0x20)[0]
e_shentsize = struct.unpack_from('<H', d, 0x2E)[0]
e_shnum = struct.unpack_from('<H', d, 0x30)[0]
e_shstrndx = struct.unpack_from('<H', d, 0x32)[0]
secs = []
for i in range(e_shnum):
    o = e_shoff + i * e_shentsize
    name, typ, flags, addr, off, size = struct.unpack_from('<IIIIII', d, o)
    secs.append(dict(nameoff=name, typ=typ, flags=flags, addr=addr, off=off, size=size))
stroff = secs[e_shstrndx]['off']
for s in secs:
    e = d.index(b'\0', stroff + s['nameoff'])
    s['name'] = d[stroff + s['nameoff']:e].decode('latin1')

cand = [s for s in secs if s['flags'] & 0x4]  # SHF_EXECINSTR
text = max(cand, key=lambda s: s['size'])
print("ELF entry=0x%08X  .text vaddr=0x%08X off=0x%X size=0x%X"
      % (struct.unpack_from('<I', d, 0x18)[0], text['addr'], text['off'], text['size']))

md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 + CS_MODE_LITTLE_ENDIAN)
md.skipdata = True
code = d[text['off']:text['off'] + text['size']]
base = text['addr']
out = open('_work_towa/dis.txt', 'w', encoding='utf-8', newline='\n')
imm = {}
n = 0
for ins in md.disasm(code, base):
    line = "0x%08X  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str)
    out.write(line + "\n"); n += 1
    for tok in ins.op_str.split(', '):
        if tok.startswith('0x'):
            try: v = int(tok, 16)
            except ValueError: continue
            imm.setdefault(v, []).append(ins.address)
out.close()
print("指令数", n, "→ _work_towa/dis.txt")
import json
json.dump({hex(k): v for k, v in sorted(imm.items())}, open('_work_towa/imm.json', 'w'), indent=0)
for k in (0x5c, 0x25, 0x26, 0x1016, 18, 3):
    print("imm 0x%X (%d): %d 处" % (k, k, len(imm.get(k, []))))
