import struct, zlib, re

P = 'iso/PSP_GAME/USRDIR/KOEID0.BIN'
_f = open(P, 'rb')
_rows = [l.split('\t') for l in open('names0.txt', encoding='utf-8').read().splitlines()]
ELF = open('iso/SYSDIR/BOOT.BIN', 'rb').read()
KEY = ELF[0x173780 + 0x54: 0x173780 + 0x54 + 55]

def entry(i):
    idx, name, a, off, size = _rows[i]; off = int(off); size = int(size)
    _f.seek(off); blob = _f.read(max(size, 1))
    if blob[:1] == b'\x78':
        try: return zlib.decompress(blob)
        except Exception: return blob
    return blob

def dec(b):
    return bytes(b[i] ^ KEY[i % 55] for i in range(len(b)))

def eem(i):
    """Return (headerFields, sectionA, sectionB) for KOEID0 entry i."""
    d = entry(i)
    if d[:4] != b'HET\x1a':
        raise ValueError('not EEM')
    h = dec(d[8:0x100])
    chkA, chkB, typ, boff, sizeA, sizeB = struct.unpack_from('<6I', h, 0)
    A = dec(d[boff:boff + sizeA])
    B = dec(d[boff + sizeA:boff + sizeA + sizeB])
    ok = (sum(A) & 0xffffffff) == chkA and (sum(B) & 0xffffffff) == chkB
    return h, A, B, ok

def all_eem_indices():
    out = []
    for i in range(1663, 2635):
        nm = _rows[i][1]
        if len(nm) == 6 and nm.isdigit():
            out.append(i)
    return out
