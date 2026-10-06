import struct, zlib, collections, sys

P = 'iso/PSP_GAME/USRDIR/KOEID0.BIN'
f = open(P, 'rb')
rows = [l.split('\t') for l in open('names0.txt', encoding='utf-8').read().splitlines()]
def get(i):
    idx, name, a, off, size = rows[i]; off = int(off); size = int(size)
    f.seek(off); blob = f.read(max(size, 1))
    if blob[:1] == b'\x78':
        try: return zlib.decompress(blob)
        except Exception: return blob
    return blob

def score(bytes_):
    good = 0
    for b in bytes_:
        if 0x20 <= b < 0x7f: good += 1
        elif 0x81 <= b <= 0x9f or 0xe0 <= b <= 0xef: good += 1
        elif 0xa1 <= b <= 0xdf: good += 1
    return good / max(1, len(bytes_))

def crack(d, per, start=0):
    n = len(d)
    key = []
    for r in range(per):
        col = [d[i] for i in range(start + r, n, per)]
        if len(col) < 10:
            key.append(0); continue
        best = (0, 0)
        for k in range(256):
            s = score(bytes(b ^ k for b in col))
            if s > best[0]: best = (s, k)
        key.append(best[1])
    return bytes(key)

for idx, label in [(1669, '000006.het'), (1663, '000000.het'), (2636, 'DIC')]:
    d = get(idx)
    key = crack(d, 55)
    out = bytes(d[i] ^ key[i % 55] for i in range(len(d)))
    print('===', label, 'key =', key.hex(' '))
    print('   raw score %.3f -> decoded score %.3f' % (score(d), score(out)))
    print('   sample:', ''.join(chr(b) if 32 <= b < 127 else '.' for b in out[:80]))
