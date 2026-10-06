#!/usr/bin/env python3
"""按路径取出 CDAR v4 里某个叶子文件: corda2f_get.py <DATA.BIN> <base> <path> <out>
path 形如 11694/25 ; 数字为各级容器内的 entry 索引。
"""
import sys, struct, zlib


def load_entry(buf, idx):
    cnt = struct.unpack_from('<I', buf, 8)[0]
    base = 0x10 + 4 * cnt
    off, dec, sz = struct.unpack_from('<III', buf, base + 12 * idx)
    return buf[off:off + sz], dec, sz


def main():
    f = open(sys.argv[1], 'rb')
    f.seek(int(sys.argv[2]))
    buf = f.read()
    path = sys.argv[3]
    out = sys.argv[4] if len(sys.argv) > 4 else None
    for i, part in enumerate(path.split('/')):
        seg, dec, sz = load_entry(buf, int(part))
        if seg[:4] == b'CDAR':
            buf = seg
        else:
            if dec != sz and seg[:1] == b'\x78':
                seg = zlib.decompress(seg)
            data = seg
    data = seg
    sys.stdout.buffer.write(data if out is None else b'')
    if out:
        open(out, 'wb').write(data)
        print(f"wrote {out} {len(data)} bytes")


if __name__ == '__main__':
    main()
