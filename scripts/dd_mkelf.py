# -*- coding: utf-8 -*-
"""把 NSO 平铺镜像包成最小 ELF64（AArch64），供 LibCpp2IL(TypeTreeGeneratorAPI) 读取。

用法: python dd_mkelf.py <flat.bin> <text.mem> <ro.mem> <data.mem> <out.elf>
"""
import sys, struct

img = open(sys.argv[1], 'rb').read()
tmem, rmem, dmem = (int(x, 0) for x in sys.argv[2:5])
out_path = sys.argv[5]

# 段大小从下一个段的 mem 起点 / 文件末尾推算
segs = [('.text', 0, tmem), ('.rodata', tmem, rmem), ('.data', rmem, dmem)]
segs = [(n, a, (segs[i + 1][2] if i + 1 < len(segs) else len(img)) - a) for i, (n, a, _) in enumerate(segs)]

BASE = 0x10000
shstr = b'\x00.text\x00.rodata\x00.data\x00.shstrtab\x00'
def no(s):
    return shstr.index(s.encode())

ehsz, phsz, shsz = 64, 56, 64
data_off = BASE
shstr_off = data_off + len(img)
sh_off = (shstr_off + len(shstr) + 7) & ~7

eh = bytearray(ehsz)
eh[0:4] = b'\x7fELF'; eh[4] = 2; eh[5] = 1; eh[6] = 1
struct.pack_into('<HHIQQQIHHHHHH', eh, 16,
                 2, 183, 1, 0, ehsz + phsz, 0, 0, ehsz, phsz, 2, 64, 5, 4)

ph = bytearray(phsz)
struct.pack_into('<IIQQQQQQ', ph, 0, 1, 5, data_off, data_off, len(img), len(img), 0x1000, 0x1000)

secs = bytearray(shsz)  # null section
for nm, addr, size in segs:
    s = bytearray(shsz)
    struct.pack_into('<IIQQQQIIQQ', s, 0, no(nm), 1, 2, BASE + addr, BASE + addr, size, 0, 0, 16, 0)
    secs += s
s = bytearray(shsz)
struct.pack_into('<IIQQQQIIQQ', s, 0, no('.shstrtab'), 3, 0, 0, 0, len(shstr), 0, 0, 1, 0)
secs += s

out = bytearray(eh) + ph
out += b'\x00' * (data_off - len(out))
out += img + shstr
out += b'\x00' * (sh_off - len(out))
out += secs
struct.pack_into('<Q', out, 40, sh_off)
struct.pack_into('<I', out, 60, 5)
open(out_path, 'wb').write(bytes(out))
print('wrote', out_path, len(out), 'sh_off', hex(sh_off))
