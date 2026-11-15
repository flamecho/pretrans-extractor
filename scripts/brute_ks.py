import sys, struct, zlib
sys.path.insert(0, '/c/game/_Trans/tools')
import ariard_xp3 as A

path = sys.argv[1]
name = sys.argv[2] if len(sys.argv) > 2 else 'scenario/10k.ks'

d, idx = A.load(path)
entry = [e for e in A.parse(idx) if e[0] == name][0]
name_, segs, adlr = entry
print('adlr =', adlr.hex() if adlr else None)
fl, off, orig, stored = segs[0]
raw = d[off:off + stored]
plain_zlib = zlib.decompressobj().decompress(raw)   # decompressed, pre-XOR
print('decompressed len', len(plain_zlib))

def score(b):
    s = 0
    for ch in b:
        if 0x20 <= ch <= 0x7e:
            s += 2
        elif ch in (0x09, 0x0a, 0x0d):
            s += 1
        elif 0x81 <= ch <= 0x9f or 0xe0 <= ch <= 0xfc or 0x30 <= ch <= 0x3f and ch == 0x30:
            s += 0
    # count cp932-ish: shift-jis lead bytes
    return s

# brute single byte
best = None
for k in range(256):
    out = bytes(b ^ k for b in plain_zlib)
    try:
        t = out.decode('cp932')
        # score: ratio of japanese + ascii
        ja = sum(1 for c in t if c >= 'ぁ')
        asc = sum(1 for c in t if 32 <= ord(c) < 127)
        if ja + asc > 0:
            sc = ja + asc
            if best is None or sc > best[0]:
                best = (sc, k, t)
    except Exception:
        pass
if best:
    print('BEST single-byte key=%02x score=%d' % (best[1], best[0]))
    print(repr(best[2][:300]))
else:
    print('no single-byte cp932 hit')

# try 4-byte adlr as repeating key
if adlr:
    out = bytes(plain_zlib[i] ^ adlr[i % 4] for i in range(len(plain_zlib)))
    try:
        t = out.decode('cp932')
        ja = sum(1 for c in t if c >= 'ぁ')
        asc = sum(1 for c in t if 32 <= ord(c) < 127)
        print('4-byte adlr key -> ja=%d asc=%d' % (ja, asc))
        print(repr(t[:300]))
    except Exception as e:
        print('4-byte adlr cp932 fail', e)
