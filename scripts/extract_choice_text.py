import sys, os, zlib, struct
sys.path.insert(0, '/c/game/_Trans/tools')
import ariard_xp3 as A

TEXT_EXT = ('.ks', '.tjs', '.txt', '.csv', '.ini', '.sav', '.asd', '.sli', '.scc')

def descramble(data):
    """Reverse KiriKiri script scramble (KirikiriDescrambler). data = zlib-decompressed payload."""
    if data[:2] != b'\xfe\xfe':
        return None  # not scrambled
    mode = data[2]
    assert data[3:5] == b'\xff\xfe', data[3:5].hex()
    body = data[5:]
    out = bytearray(len(body))
    if mode == 0:
        for i in range(0, len(body) - 1, 2):
            lo, hi = body[i], body[i + 1]
            if hi == 0 and lo < 0x20:
                out[i], out[i + 1] = lo, hi
                continue
            hi ^= (lo & 0xFE)
            lo ^= 1
            out[i], out[i + 1] = lo, hi
    elif mode == 1:
        for i in range(0, len(body) - 1, 2):
            c = body[i] | (body[i + 1] << 8)
            c = ((c & 0xAAAA) >> 1) | ((c & 0x5555) << 1)
            out[i] = c & 0xff
            out[i + 1] = (c >> 8) & 0xff
    elif mode == 2:
        cl, ul = struct.unpack_from('<qq', body, 0)
        d = zlib.decompressobj(-15)
        ud = d.decompress(body[18:])
        return ud.decode('utf-16-le', 'replace')
    else:
        raise ValueError('unsupported scramble mode %d' % mode)
    return out.decode('utf-16-le', 'replace')


def load_payloads(path):
    """Return {name: zlib-decompressed payload bytes} for all text-ish entries."""
    d, idx = A.load(path)
    res = {}
    for name, segs, adlr in A.parse(idx):
        if not name or not name.lower().endswith(TEXT_EXT):
            continue
        parts = []
        ok = True
        for fl, off, orig, stored in segs:
            raw = d[off:off + stored]
            if fl == 1:
                try:
                    raw = zlib.decompressobj().decompress(raw)
                except Exception:
                    ok = False
                    break
            parts.append(raw)
        if ok and parts:
            res[name] = b''.join(parts)
    return res


def main():
    data_xp3, patch_xp3, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(outdir, exist_ok=True)
    payloads = load_payloads(data_xp3)
    payloads.update(load_payloads(patch_xp3))  # patch overrides
    n_total = len(payloads)
    n_scrambled = 0
    n_text = 0
    for name, payload in sorted(payloads.items()):
        dec = descramble(payload)
        if dec is None:
            continue  # not a scrambled script
        n_scrambled += 1
        # write utf-16-le scramble-free text as utf-8
        rel = name.replace('\\', '/')
        dst = os.path.join(outdir, rel + '.txt')
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, 'w', encoding='utf-8', newline='') as g:
            g.write(dec)
        n_text += 1
    print('entries(text-ext): %d | scrambled&decoded: %d' % (n_total, n_scrambled))
    print('wrote %d text files to %s' % (n_text, outdir))


if __name__ == '__main__':
    main()
