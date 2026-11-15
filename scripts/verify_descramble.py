import sys, zlib
sys.path.insert(0, '/c/game/_Trans/tools')
import ariard_xp3 as A

def descramble(data):
    assert data[:2] == b'\xfe\xfe', data[:2].hex()
    mode = data[2]
    assert data[3:5] == b'\xff\xfe', data[3:5].hex()
    body = data[5:]
    out = bytearray(len(body))
    if mode == 0:
        for i in range(0, len(body)-1, 2):
            lo, hi = body[i], body[i+1]
            if hi == 0 and lo < 0x20:
                out[i], out[i+1] = lo, hi
                continue
            hi ^= (lo & 0xFE)
            lo ^= 1
            out[i], out[i+1] = lo, hi
    elif mode == 1:
        for i in range(0, len(body)-1, 2):
            c = body[i] | (body[i+1] << 8)
            c = ((c & 0xAAAA) >> 1) | ((c & 0x5555) << 1)
            out[i] = c & 0xff
            out[i+1] = (c >> 8) & 0xff
    elif mode == 2:
        import struct, io
        cl, ul = struct.unpack_from('<qq', body, 0)
        raw = body[16:]  # skip 16 (cl, ul) + 2 (zlib header already in raw deflate)
        # .NET DeflateStream expects raw deflate; strip the 2-byte zlib header
        from gzip import decompress as _g
        # use zlib raw
        d = zlib.decompressobj(-15)
        ud = d.decompress(body[18:])
        return ud.decode('utf-16-le', 'replace')
    else:
        raise ValueError('mode %d' % mode)
    return out.decode('utf-16-le', 'replace')

path = sys.argv[1]
name = sys.argv[2] if len(sys.argv) > 2 else 'scenario/10k.ks'
d, idx = A.load(path)
entry = [e for e in A.parse(idx) if e[0] == name][0]
fl, off, orig, stored = entry[1][0]
raw = d[off:off+stored]
pz = zlib.decompressobj().decompress(raw)
print('=== %s (stored=%d decompressed=%d) ===' % (name, stored, len(pz)))
print('header:', pz[:6].hex(' '))
t = descramble(pz)
print('--- decoded head (first 600 chars) ---')
print(t[:600])
