#!/usr/bin/env python3
"""Orange Honey (PS2, guyzware) — PETA(PTH/PTD) 解包

链路: PTH(PETA 头 0x20 + 全局 SBOX 256B + 加密索引 0x120)
      → SBOX/递减异或解出索引 → 条目 [u32 off][u32 size][u32 flag][u32 pad][name]
      → PTD 内 YKLZ(LZSS, shift=param-8, 0x10 起) 解压 → .OHS 脚本
"""
import struct, os, sys


def yklz_decompress(data):
    if len(data) < 16 or data[:4] != b'YKLZ':
        return data
    param = data[7]
    shift = param - 8 if param >= 8 else 4
    mask = (1 << shift) - 1
    size = struct.unpack('<I', data[8:12])[0]
    src = 0x10
    out = bytearray()
    while len(out) < size and src < len(data):
        flags = data[src]; src += 1
        for _ in range(8):
            if len(out) >= size or src >= len(data):
                break
            isref = (flags & 0x80) != 0
            flags = (flags << 1) & 0xFF
            if not isref:
                out.append(data[src]); src += 1
            else:
                if src + 1 >= len(data):
                    break
                b1 = data[src]; b2 = data[src + 1]; src += 2
                length = (b1 >> shift) + 3
                off = (((b1 & mask) << 8) | b2) + 1
                start = len(out) - off
                for i in range(length):
                    idx = start + i
                    out.append(0 if idx < 0 else out[idx])
    return bytes(out)


def decode_index(pth):
    sbox = pth[0x20:0x120]
    enc = pth[0x120:]
    out = bytearray()
    t = 0
    for b in enc:
        out.append(sbox[(t ^ b) & 0xFF])
        t = (t - 1) & 0xFF
    return bytes(out)


def parse_index(pth, ptd_len):
    idx = decode_index(pth)
    rows = []
    p = 0
    while p + 0x30 <= len(idx):
        a, b, c, d = struct.unpack_from('<4I', idx, p)
        nm = idx[p + 0x10:p + 0x50].split(b'\x00')[0]
        p += 0x10
        if not nm or not (0x20 <= nm[0] <= 0x7e):
            continue
        try:
            s = nm.decode('ascii')
        except UnicodeDecodeError:
            continue
        if d != 0 or b == 0 or a >= ptd_len or '/' in s:
            continue
        rows.append((a, b, c, s))
    return rows


def main(pth_path, ptd_path, outdir):
    pth = open(pth_path, 'rb').read()
    ptd = open(ptd_path, 'rb').read()
    rows = parse_index(pth, len(ptd))
    os.makedirs(outdir, exist_ok=True)
    ok = bad = 0
    for a, b, c, name in rows:
        raw = ptd[a:a + b]
        dec = yklz_decompress(raw) if c else raw
        if dec[:4] != b'\xb5\xda\xca\xc6':
            print('  [warn] %-18s off=%08x flag=%d magic=%s' % (name, a, c, dec[:4].hex()))
            bad += 1
        else:
            ok += 1
        open(os.path.join(outdir, name), 'wb').write(dec)
    print('entries=%d ok=%d warn=%d' % (len(rows), ok, bad))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
