import sys, zlib
sys.path.insert(0, '/c/game/_Trans/tools')
import ariard_xp3 as A
TEXT_EXT = ('.ks', '.tjs', '.txt', '.csv', '.ini', '.sav', '.asd', '.sli', '.scc')

def payloads(path):
    d, idx = A.load(path)
    res = {}
    for name, segs, adlr in A.parse(idx):
        if not name or not name.lower().endswith(TEXT_EXT):
            continue
        parts = []; ok = True
        for fl, off, orig, stored in segs:
            raw = d[off:off + stored]
            if fl == 1:
                try:
                    raw = zlib.decompressobj().decompress(raw)
                except Exception:
                    ok = False; break
            parts.append(raw)
        if ok and parts:
            res[name] = b''.join(parts)
    return res

r = payloads(sys.argv[1]); r.update(payloads(sys.argv[2]))
nos = []
for n, p in sorted(r.items()):
    if p[:2] != b'\xfe\xfe':
        nos.append((n, p[:4].hex(), p[:60]))
print('non-scrambled count:', len(nos))
for n, h, b in nos[:50]:
    try:
        t = b.decode('utf-16-le', 'replace'); dec = 'u16'
    except Exception:
        t = b.decode('cp932', 'replace'); dec = 'cp932'
    print(n, '|', h, '|', dec, '|', repr(t[:50]))
