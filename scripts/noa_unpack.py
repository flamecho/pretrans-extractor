# -*- coding: utf-8 -*-
"""Entis GLS / ERISA 'noa' archive unpacker.

Format (verified on 自律機動戦車イヅナ 2006 TEA-CROWN, byte-exact closure):
  0x00  char[6]  "Entis\x1a"
  0x10  char[24] "ERISA-Archive file"
  0x40  char[16] "DirEntryA" / "DirEntry6"  (version tag)
  0x50  u32      entry count
  0x54  records, each:
          u64 size            (stored byte length == logical length, no compression)
          u64 0
          u64 off_raw         absolute data offset = off_raw + 0x50
          u64 FILETIME
          u32 0
          u32 namelen         (includes trailing NUL)
          char name[namelen]  cp932
  Data blocks are RAW (verified: *.ico opens, internal offsets resolve).
  Each block is followed by a 16-byte gap before the next block.
"""
import os, struct, sys

MAGIC = b'Entis\x1a'
BASE = 0x50


def parse(path):
    d = open(path, 'rb').read()
    assert d[:6] == MAGIC, 'not a noa archive: %r' % d[:6]
    cnt = struct.unpack_from('<I', d, 0x50)[0]
    off = 0x54
    ents = []
    for _ in range(cnt):
        size, z, raw, ft, z2, nl = struct.unpack_from('<QQQQII', d, off)
        nm = d[off + 40: off + 40 + nl].split(b'\x00')[0]
        ents.append({'name': nm.decode('cp932', 'replace'), 'size': size, 'off': raw + BASE})
        off += 40 + nl
    return d, ents


def unpack(path, outdir):
    d, ents = parse(path)
    tot = 0
    for e in ents:
        p = os.path.join(outdir, e['name'])
        d0 = os.path.dirname(p)
        if d0:
            os.makedirs(d0, exist_ok=True)
        open(p, 'wb').write(d[e['off']:e['off'] + e['size']])
        tot += e['size']
    print('%s: %d entries, %d bytes, data %d, filesize %d'
          % (os.path.basename(path), len(ents), tot, sum(e['size'] for e in ents), len(d)))


if __name__ == '__main__':
    unpack(sys.argv[1], sys.argv[2])
