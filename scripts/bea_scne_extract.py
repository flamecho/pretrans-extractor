import struct, sys, os, json
import zstandard as zstd

def read_bea(path):
    b = open(path, 'rb').read()
    assert b[:4] == b'SCNE', b[:4]
    n = struct.unpack_from('<H', b, 0x20)[0]
    ptr_tab = struct.unpack_from('<Q', b, 0x28)[0]
    dic = struct.unpack_from('<Q', b, 0x30)[0]
    name_addr = struct.unpack_from('<Q', b, 0x40)[0]
    out = []
    for i in range(n):
        off = struct.unpack_from('<Q', b, ptr_tab + 8 * i)[0]
        assert b[off:off+4] == b'ASST', (i, b[off:off+4])
        comp = b[off+0x10]
        align = struct.unpack_from('<H', b, off+0x12)[0]
        csize = struct.unpack_from('<I', b, off+0x14)[0]
        dsize = struct.unpack_from('<I', b, off+0x18)[0]
        caddr = struct.unpack_from('<Q', b, off+0x20)[0]
        naddr = struct.unpack_from('<Q', b, off+0x28)[0]
        nlen = struct.unpack_from('<H', b, naddr)[0]
        name = b[naddr+2:naddr+2+nlen].decode('utf-8')
        out.append(dict(index=i, name=name, comp=comp, align=align, csize=csize,
                        dsize=dsize, caddr=caddr, naddr=naddr))
    return b, out

def extract(path, outdir, pattern=None, verbose=False):
    b, entries = read_bea(path)
    print(f"{os.path.basename(path)}: {len(entries)} entries, size {len(b)}")
    comps = {}
    dctx = zstd.ZstdDecompressor()
    n_ok = 0
    for e in entries:
        comps[e['comp']] = comps.get(e['comp'], 0) + 1
        if pattern and not e['name'].startswith(pattern):
            continue
        data = b[e['caddr']:e['caddr']+e['csize']]
        if e['comp'] == 2:
            d = dctx.decompress(data, max_output_size=e['dsize'])
        elif e['comp'] == 1:
            import zlib
            d = zlib.decompress(data)
        elif e['comp'] == 0:
            d = data
        else:
            raise ValueError(f"unknown comp {e['comp']}")
        if len(d) != e['dsize']:
            print("SIZE MISMATCH", e['name'], len(d), e['dsize'])
        dst = os.path.join(outdir, e['name'].replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(d)
        n_ok += 1
        if verbose:
            print(" ", e['name'], e['csize'], '->', len(d))
    print("comp distribution", comps, "extracted", n_ok)
    return entries

if __name__ == '__main__':
    src = sys.argv[1]
    out = sys.argv[2]
    pat = sys.argv[3] if len(sys.argv) > 3 else None
    extract(src, out, pat, verbose=('-v' in sys.argv))
