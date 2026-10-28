"""列 NSP 内 PFS0 条目（名 / 偏移 / 大小），顺带提示 ticket 的 keygen 与 cert 尺寸。"""
import sys, struct, os

def pfs0(path):
    f = open(path, 'rb')
    hdr = f.read(0x10)
    magic, cnt, strtab_size, _ = struct.unpack('<4sIII', hdr)
    assert magic == b'PFS0', magic
    ents = []
    for i in range(cnt):
        d = f.read(0x18)
        off, size, nameoff, _r = struct.unpack('<QQII', d)
        ents.append([off, size, nameoff])
    strtab = f.read(strtab_size)
    base = 0x10 + 0x18 * cnt + strtab_size
    out = []
    for off, size, nameoff in ents:
        name = strtab[nameoff:strtab.index(b'\0', nameoff)].decode()
        out.append((name, base + off, size))
    return out, base

def main():
    nsp = sys.argv[1]
    ents, base = pfs0(nsp)
    print('base=0x%X total=%d' % (base, len(ents)))
    f = open(nsp, 'rb')
    for name, off, size in ents:
        print('%-40s off=0x%-10X size=%d' % (name, off, size))
        if name.endswith('.tik'):
            f.seek(off)
            tik = f.read(size)
            print('   tik sigtype=%d' % struct.unpack('<I', tik[0:4])[0])
            print('   rights/titleid@0x2A0 =', tik[0x2A0:0x2B0].hex())
            print('   titlekey_block@0x180 =', tik[0x180:0x190].hex())
            print('   keygen? @0x281 =', tik[0x280:0x2A0].hex())
        if name.endswith('.cert'):
            print('   cert size', size)

main()
