import sys, zlib, collections, re
sys.path.insert(0, '/c/game/_Trans/tools')
import ariard_xp3 as A

# ---- edema_xp3 decode logic (cxdec two-segment single-byte XOR via CRLF anchors) ----
BAD_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ufffd\ue000-\uf8ff'
                    r'\uac00-\ud7af\ud800-\udfff\u0400-\u04ff\u0e00-\u0e7f\u0600-\u06ff]')
H_SET = frozenset([0x00, 0x20, 0x21, 0x25, 0x26, 0x30, 0xFF]) | frozenset(range(0x4E, 0xA0))

def anchors16(c):
    return [(q, c[q + 1]) for q in range(0, len(c) - 3)
            if c[q] ^ c[q + 1] == 0x0D and c[q + 2] ^ c[q + 3] == 0x0A
            and c[q + 1] == c[q + 3]]

def anchors8_all(c):
    return [(q, c[q] ^ 0x0D) for q in range(0, len(c) - 1)
            if c[q] ^ c[q + 1] == 0x07]

def xor2(c, k1, k2, b):
    d = bytearray(c)
    for i in range(min(b, len(d))):
        d[i] ^= k1
    for i in range(b, len(d)):
        d[i] ^= k2
    return bytes(d)

def to_text(d, mode):
    if mode == "utf16":
        return d.decode("utf-16-le", "replace").lstrip("\ufeff")
    return d.decode("cp932", "replace")

def decode(name, c):
    a16 = anchors16(c)
    mode = "utf16" if a16 else "cp932"
    hs, tail = (a16, 4) if mode == "utf16" else (anchors8_all(c), 2)
    if not hs:
        t = to_text(c, mode)
        return mode, t, 0, 0, 0, len(BAD_RE.findall(t))
    head = [k for q, k in hs if q < 1000]
    k1 = collections.Counter(head).most_common(1)[0][0] if head else 0
    tail_a = [k for q, k in hs if q >= max(0, len(c) - 1500)]
    k2 = collections.Counter(tail_a).most_common(1)[0][0] if tail_a else k1
    trust = [(q, k) for q, k in hs if k in (k1, k2)] or hs
    nB = sum(1 for _, k in trust if k == k2)
    best, nA, nBs = (-1, 0), 0, nB
    for i, (q, k) in enumerate(trust):
        if nA + nBs > best[0]:
            best = (nA + nBs, i)
        if k == k1:
            nA += 1
        else:
            nBs -= 1
    i = best[1]
    lo = trust[i - 1][0] + tail if i > 0 else 0
    hi = trust[i][0] if i < len(trust) else len(c)
    if hi < lo:
        lo, hi = hi, lo
    hi = min(hi, lo + 512)
    def score(b):
        d = xor2(c, k1, k2, b)
        t = to_text(d, mode)
        nb = len(BAD_RE.findall(t))
        if mode == 'utf16':
            bad_hi = sum(1 for i in range(2, len(d) - 1, 2) if d[i + 1] not in H_SET)
            return -(bad_hi + 20 * nb)
        return -nb
    step = 2 if mode == 'utf16' else 1
    start = lo if lo % step == 0 else lo + (step - lo % step)
    bb, bn = start, None
    for b in range(start, hi + 1, step):
        s = score(b)
        if bn is None or s > bn:
            bn, bb = s, b
    t = to_text(xor2(c, k1, k2, bb), mode)
    return mode, t, k1, k2, bb, len(BAD_RE.findall(t))

# ---- loader (ariard, index @0x20) ----
path = sys.argv[1]
name = sys.argv[2] if len(sys.argv) > 2 else 'scenario/10k.ks'
d, idx = A.load(path)
entry = [e for e in A.parse(idx) if e[0] == name][0]
fl, off, orig, stored = entry[1][0]
c = zlib.decompressobj().decompress(d[off:off+stored])
print('decompressed len', len(c))
mode, t, k1, k2, b, nb = decode(name, c)
print('mode=%s k1=%02x k2=%02x bnd=%d bad=%d' % (mode, k1, k2, b, nb))
print('--- text head ---')
print(t[:600])
