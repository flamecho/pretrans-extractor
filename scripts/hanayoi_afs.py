import sys, os, struct

def parse_afs(path):
    with open(path, 'rb') as f:
        data = f.read()
    assert data[:4] == b'AFS\x00', data[:4]
    count = struct.unpack_from('<I', data, 4)[0]
    entries = []
    off = 8
    for i in range(count):
        o, s = struct.unpack_from('<II', data, off)
        off += 8
        entries.append((o, s))
    return data, entries

def main():
    path = sys.argv[1]
    outdir = sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    data, entries = parse_afs(path)
    base = os.path.splitext(os.path.basename(path))[0]
    print(f"{path}: {len(data)} bytes, {len(entries)} files")
    for i, (o, s) in enumerate(entries):
        blob = data[o:o+s]
        fn = os.path.join(outdir, f"{base}_{i:03d}.bin")
        with open(fn, 'wb') as f:
            f.write(blob)
        # peek signature
        sig = blob[:16]
        print(f"  [{i:03d}] off=0x{o:08X} size={s:9d} sig={sig!r}")

if __name__ == '__main__':
    main()
