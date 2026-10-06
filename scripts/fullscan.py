import struct, zlib, pickle, re, sys

def find_table(d):
    n = len(d)
    for base in (0x20, 0x40):
        cnt_max = (n - base) // 16
        if cnt_max <= 0: continue
        recs = [struct.unpack_from('<IIII', d, base+16*i) for i in range(cnt_max)]
        best = 0
        for i,(no,pk,off,sz) in enumerate(recs):
            csize = pk >> 8
            if off == 0 and csize == 0: best = i+1; continue
            if off + csize <= n: best = i+1; continue
            break
        if best >= 1: return base, best, recs[:best]
    return None

def entry_data(d, pk, off, sz):
    if not off or not sz: return b''
    blob = d[off:off+(pk>>8)]
    if (pk & 0xFF) == 2:
        try: return zlib.decompress(blob)
        except Exception: return blob
    return blob

def nameof(d, no):
    if not (0 < no < len(d)): return ''
    e = d.find(b'\x00', no)
    if e < 0 or e-no > 128: return ''
    try: return d[no:e].decode('cp932')
    except Exception: return ''

recs = pickle.load(open('kd1recs.pkl','rb'))
f = open('iso/PSP_GAME/USRDIR/KOEID1.BIN','rb')
out = []
for j, nm, off, sz in recs:
    f.seek(off); d = f.read(sz)
    r = find_table(d)
    if not r:
        out.append((nm, None, 0, 0)); continue
    base, cnt, ent = r
    tot = 0
    for (no, pk, o, s) in ent:
        blob = entry_data(d, pk, o, s)
        if not blob: continue
        jp = 0
        i = 0; L=len(blob)
        while i < L-1:
            b = blob[i]
            if 0x81 <= b <= 0x9f or 0xe0 <= b <= 0xef:
                try:
                    c = blob[i:i+2].decode('cp932')
                    if '\u3041'<=c<='\u309f' or '\u30a1'<=c<='\u30ff' or '\u4e00'<=c<='\u9fff': jp+=1
                except Exception: pass
                i+=2
            else: i+=1
        if jp: out.append((nm, nameof(d,no), o, jp))
    print('done', j, nm, file=sys.stderr)
pickle.dump(out, open('fullscan.pkl','wb'))
agg = {}
for nm2, fn, o, jp in out:
    agg[nm2] = agg.get(nm2, 0) + jp
print('=== archives by jp chars ===')
for k,v in sorted(agg.items(), key=lambda kv:-kv[1])[:30]:
    print(k, v)
print('=== entries with most jp ===')
e2 = [x for x in out if x[1] is not None]
e2.sort(key=lambda x:-x[3])
for x in e2[:60]: print(x)
