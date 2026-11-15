import sys, zlib, re
sys.path.insert(0, '/c/game/_Trans/tools')
import ariard_xp3 as A

path = sys.argv[1]
name = sys.argv[2] if len(sys.argv) > 2 else 'scenario/10k.ks'
d, idx = A.load(path)
entry = [e for e in A.parse(idx) if e[0] == name][0]
fl, off, orig, stored = entry[1][0]
c = zlib.decompressobj().decompress(d[off:off+stored])
N = len(c)
print('len', N, flush=True)

BAD_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ufffd\ue000-\uf8ff'
                    r'\uac00-\ud7af\ud800-\udfff\u0400-\u04ff\u0e00-\u0e7f\u0600-\u06ff]')
H_SET = frozenset([0x00, 0x20, 0x21, 0x25, 0x26, 0x30, 0xFF]) | frozenset(range(0x4E, 0xA0))
def bad_hi(out):
    return sum(1 for i in range(2, len(out)-1, 2) if out[i+1] not in H_SET)
def score(out):
    return bad_hi(out) + 20*len(BAD_RE.findall(out.decode('utf-16-le','replace')))

def xor_rep(data, key):
    out = bytearray(len(data))
    for i, b in enumerate(data):
        out[i] = b ^ key[i % len(key)]
    return bytes(out)

cands = []
for pw in ['otoame', 'OTOAME', 'otoame\n', 'Otoame', 'otoame ', 'amoroso', 'CHOICE', 'choice']:
    for enc in ('utf-16-le', 'utf-8', 'cp932'):
        try:
            key = pw.encode(enc)
        except Exception:
            continue
        out = xor_rep(c, key)
        sc = score(out)
        t = out.decode('utf-16-le', 'replace')
        ja = sum(1 for ch in t if ch >= 'ぁ')
        print('pw=%r enc=%s keylen=%d score=%d ja=%d' % (pw, enc, len(key), sc, ja), flush=True)
        # also try just first 4/8 bytes as key
        if sc < 2000:
            print('  POSSIBLE:', repr(t[:200]))
print('done')
