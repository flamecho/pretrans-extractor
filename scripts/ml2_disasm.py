#!/usr/bin/env python3
"""最小 MIPS R5900 反汇编器（capstone 封装）——用于读 SLPM 里的解压函数。

用法: python scripts/ml2_disasm.py <elf> <vaddr_hex> <bytes_len> [--base]
"""
import sys, struct
from capstone import *

def elf_phdrs(path):
    d = open(path, 'rb').read()
    assert d[:4] == b'\x7fELF'
    e_phoff, = struct.unpack_from('<I', d, 0x1c)
    e_phentsize, e_phnum = struct.unpack_from('<HH', d, 0x2a)
    out = []
    for i in range(e_phnum):
        o = e_phoff + i * e_phentsize
        p_type, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz = struct.unpack_from('<IIIIII', d, o)
        if p_type == 1:
            out.append((p_vaddr, p_offset, p_filesz))
    return d, out

def v2o(phdrs, vaddr):
    for v, o, sz in phdrs:
        if v <= vaddr < v + sz:
            return o + (vaddr - v)
    return None

def main():
    elf, va = sys.argv[1], int(sys.argv[2], 16)
    n = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0x600
    d, ph = elf_phdrs(elf)
    off = v2o(ph, va)
    if off is None:
        print('vaddr not in any PT_LOAD'); return
    code = d[off:off+n]
    md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 + CS_MODE_LITTLE_ENDIAN)
    md.detail = True
    pos = 0
    while pos < len(code):
        hit = False
        for ins in md.disasm(code[pos:pos + 4], va + pos):
            print('%08x: %-24s %s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
            hit = True
        if not hit:
            print('%08x: %-24s .word 0x%08x' % (va + pos, code[pos:pos + 4].hex(),
                                                struct.unpack_from('<I', code, pos)[0]))
        pos += 4

if __name__ == '__main__':
    main()
