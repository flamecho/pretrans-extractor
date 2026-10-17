#!/usr/bin/env python3
"""罪喰い for V (PCSG01019, HuneX Ogre) allscr.mrg 解包 + MZX0 解压。
用法: python scripts/zokuwanai_unpack.py <allscr.mrg> <outdir>
"""
import struct, os, sys
from io import BytesIO

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hunex'))
from hunex_decomp_mzx0 import mzx0_decompress


def mrgd00_members(d):
    assert d[:6] == b'mrgd00', "not mrgd00"
    n = struct.unpack_from('<H', d, 6)[0]
    base = 8 + n * 8
    out = []
    for i in range(n):
        so, of, su, sz = struct.unpack_from('<4H', d, 8 + i * 8)
        off = base + so * 0x800 + of
        size = (su - 1) // 0x20 * 0x10000 + sz
        out.append(d[off:off + size])
    return n, out


def decompress_mzx0(blob, xorff=True):
    if blob[:4] != b'MZX0':
        return blob
    exlen = struct.unpack_from('<I', blob, 4)[0]
    f = BytesIO(blob[8:])
    st, bio = mzx0_decompress(f, len(blob) - 8, exlen, xorff=xorff)
    return bio.read()


def main():
    src = sys.argv[1]
    outdir = sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    d = open(src, 'rb').read()
    n, members = mrgd00_members(d)
    # member[0] = scr.nam
    names = []
    nm = members[0]
    for k in range(0, len(nm), 32):
        names.append(nm[k:k + 32].rstrip(b'\0\r\n').decode('cp932', 'replace'))
    # member[3..] = scripts; name for member[i] = names[i-3]
    print("mrgd00 count=%d, names=%d, scripts=%d" % (n, len(names), n - 3))
    idx = []
    for i in range(3, n):
        name = names[i - 3] if i - 3 < len(names) else ''
        blob = members[i]
        dec = decompress_mzx0(blob)
        fn = "%03d_%s.txt" % (i - 3, name or 'NONAME')
        open(os.path.join(outdir, fn), 'wb').write(dec)
        idx.append((i - 3, name, len(dec), blob[:4] == b'MZX0'))
    print("wrote", len(idx), "scripts to", outdir)


if __name__ == '__main__':
    main()
