import struct, zlib, math, collections, itertools

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

def ent(b):
    n = len(b)
    if n == 0: return 0
    c = collections.Counter(b)
    return -sum(v/n*math.log2(v/n) for v in c.values())

def pr(b):
    return sum(1 for x in b if 32 <= x < 127)/max(1, len(b))

def lzss(data, flag_first1, lit_is_1, split_off_bits, minlen):
    out = bytearray()
    i = 0; n = len(data)
    while i < n:
        flag = data[i]; i += 1
        bits = [ (flag >> (7-k)) & 1 for k in range(8) ] if flag_first1 else [ (flag >> k) & 1 for k in range(8) ]
        for bit in bits:
            if i >= n: break
            is_lit = (bit == 1) if lit_is_1 else (bit == 0)
            if is_lit:
                out.append(data[i]); i += 1
            else:
                if i+1 >= n: break
                b1, b2 = data[i], data[i+1]; i += 2
                v = (b1 << 8) | b2
                lenbits = 16 - split_off_bits - minlen
                if lenbits <= 0: break
                ln = (v >> split_off_bits) + minlen
                disp = v & ((1 << split_off_bits) - 1)
                if disp == 0: break
                for _ in range(ln):
                    if disp > len(out): break
                    out.append(out[-disp])
    return bytes(out)

def lz_bios(data):
    out = bytearray(); i = 0; n = len(data)
    while i < n:
        flag = data[i]; i += 1
        for k in range(8):
            if i >= n: break
            if (flag >> (7-k)) & 1:
                out.append(data[i]); i += 1
            else:
                if i+1 >= n: break
                b1, b2 = data[i], data[i+1]; i += 2
                ln = (b1 >> 4) + 3
                disp = ((b1 & 0xF) << 8) | b2
                for _ in range(ln):
                    if disp > len(out): break
                    out.append(out[-disp])
    return bytes(out)

d = get(1669)
body = d[0x10:]
cands = []
cands.append(('bios', lz_bios(body)))
for fs in (True, False):
    for li in (True, False):
        for sb in (8, 10, 11, 12, 13):
            for ml in (1, 2, 3, 4):
                try:
                    o = lzss(body, fs, li, sb, ml)
                except Exception:
                    continue
                cands.append(('lzss f1=%s lit1=%s off=%d min=%d' % (fs, li, sb, ml), o))
scored = []
for name, o in cands:
    if len(o) < 500: continue
    scored.append((ent(o), pr(o), len(o), name))
scored.sort()
print('lowest output entropy:')
for e, p, l, nm in scored[:15]:
    print('  H=%.2f print=%.2f len=%d  %s' % (e, p, l, nm))
print('raw body H=%.2f print=%.2f' % (ent(body), pr(body)))
