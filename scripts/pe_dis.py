import struct, sys
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import capstone as C
import capstone.x86 as X

path = os.path.join(VNTRANS_HOME, '<psvdec>/bin/win64/psvpfsparser.exe')
data = bytearray(open(path, 'rb').read())
e_lfanew = struct.unpack_from('<I', data, 0x3C)[0]
coff = e_lfanew + 4
num_sec = struct.unpack_from('<H', data, coff + 2)[0]
opt_size = struct.unpack_from('<H', data, coff + 16)[0]
opt_off = coff + 20
magic = struct.unpack_from('<H', data, opt_off)[0]
image_base = struct.unpack_from('<Q', data, opt_off + 24)[0]
sec_off = opt_off + opt_size
secs = []
for i in range(num_sec):
    o = sec_off + i * 40
    name = bytes(data[o:o+8]).rstrip(b'\0')
    vsize, vaddr, rawsize, rawptr = struct.unpack_from('<IIII', data, o + 8)
    secs.append((name, vaddr, vsize, rawptr, rawsize))
print('image_base', hex(image_base))

def rva2off(rva):
    for name, vaddr, vsize, rawptr, rawsize in secs:
        if vaddr <= rva < vaddr + max(vsize, rawsize):
            return rawptr + (rva - vaddr)
    return None

def off2rva(off):
    for name, vaddr, vsize, rawptr, rawsize in secs:
        if rawptr <= off < rawptr + rawsize:
            return vaddr + (off - rawptr)
    return None

strs = {}
for s in [b'header signature is invalid\x00', b'verifying header...\x00', b'root icv is invalid\x00',
          b'header signature is valid\x00', b'root icv is valid\x00']:
    off = data.find(s)
    if off >= 0:
        va = image_base + off2rva(off)
        strs[va] = s
        print(repr(s), 'va', hex(va))

text = [s for s in secs if s[0] == b'.text'][0]
tname, tvaddr, tvsize, trawptr, trawsize = text
code = bytes(data[trawptr:trawptr + trawsize])
md = C.Cs(C.CS_ARCH_X86, C.CS_MODE_64)
md.detail = True

hits = []
for ins in md.disasm(code, image_base + tvaddr):
    if ins.id == X.X86_INS_LEA and len(ins.operands) == 2:
        m = ins.operands[1]
        if m.type == X.X86_OP_MEM and m.mem.base == X.X86_REG_RIP:
            tgt = ins.address + ins.size + m.mem.disp
            if tgt in strs:
                hits.append((ins.address, tgt, strs[tgt]))
for addr, tgt, s in hits:
    print('REF', hex(addr), '->', s)

# print context around the two "invalid" refs
for addr, tgt, s in hits:
    if b'invalid' not in s:
        continue
    print('\n==== context for', s, 'at', hex(addr), '====')
    start = addr - 0x100
    s_off = rva2off(start - image_base)
    s_rva = off2rva(s_off)
    chunk = code[s_off - trawptr: s_off - trawptr + 0x180]
    for ins2 in md.disasm(chunk, image_base + s_rva):
        mark = ''
        if ins2.address == addr:
            mark = '   <<<< HERE'
        print(f'  {ins2.address:#012x}  {ins2.mnemonic:8s} {ins2.op_str}{mark}')
