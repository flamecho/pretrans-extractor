# -*- coding: utf-8 -*-
"""金色のコルダ2 ff : Koei G1T (GT1G0600) 字体图集解码 -> PNG
条目: entry(8B: mipUnk,format,dimension,zero0,swizzle,unk3,unk4,extHeader)
      + u32 extHeaderSize + (extHeaderSize-4)B
      + W*H*bpp/8 像素;  W=2^(dim&0xF), H=2^((dim>>4)&0xF)
格式: Vita 表 0x12/0x08=DXT5, 0x10/0x06=DXT1, 0x00=RGBA8888, 0x01=BGRA8888
"""
import struct, zlib, sys, os

VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
PATH = os.path.join(VNTRANS_HOME, 'tmp_c2ff/dec/DATA.BIN')


def gen(data, label, depth=0):
    if data[:4] != b'CDAR':
        return
    unk1, count, unk2 = struct.unpack_from('<III', data, 4)
    base = 16 + count * 4
    for i in range(count):
        o, ds, sz = struct.unpack_from('<III', data, base + 12 * i)
        if sz == 0 or o + sz > len(data):
            continue
        raw = data[o:o + sz]
        d = zlib.decompress(raw) if raw[:2] in (b'\x78\x9c', b'\x78\x01', b'\x78\xda') else raw
        lab = f'{label}#{i:05d}'
        if d[:4] == b'CDAR' and depth < 4:
            yield from gen(d, lab, depth + 1)
        else:
            yield lab, d


def parse_g1t(d):
    magic = d[:8]
    size, dataOffset, texCount, unk1, unk2 = struct.unpack_from('<IIIII', d, 8)
    offs = list(struct.unpack_from('<%dI' % texCount, d, dataOffset))
    out = []
    for off in offs:
        p = dataOffset + off
        mipUnk, fmt, dim, zero0, swz, u3, u4, extH = d[p:p + 8]
        q = p + 8
        if extH > 0:
            ehs = struct.unpack_from('<I', d, q)[0]
            q += ehs
        W = 1 << (dim & 0xF)
        H = 1 << ((dim >> 4) & 0xF)
        bpp = {0x00: 32, 0x01: 32, 0x06: 4, 0x08: 8, 0x10: 4, 0x12: 8}.get(fmt)
        if bpp is None:
            out.append((fmt, W, H, None, swz))
            continue
        n = W * H * bpp // 8
        out.append((fmt, W, H, d[q:q + n], swz))
    return magic, texCount, out


# ---------------- DXT 解码 ----------------
def _rgb565(c):
    r = (c >> 11) & 0x1F
    g = (c >> 5) & 0x3F
    b = c & 0x1F
    return (r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)


def decode_dxt(data, W, H, bc3=True):
    px = bytearray(W * H * 4)
    bw = W // 4
    for by in range(H // 4):
        for bx in range(bw):
            off = (by * bw + bx) * 16
            blk = data[off:off + 16]
            if len(blk) < 16:
                continue
            c0, c1 = struct.unpack_from('<HH', blk, 8)
            bits = int.from_bytes(blk[12:16], 'little')
            r0, g0, b0 = _rgb565(c0)
            r1, g1, b1 = _rgb565(c1)
            cols = [(r0, g0, b0, 255), (r1, g1, b1, 255)]
            if c0 > c1:
                cols.append(((2 * r0 + r1) // 3, (2 * g0 + g1) // 3, (2 * b0 + b1) // 3, 255))
                cols.append(((r0 + 2 * r1) // 3, (g0 + 2 * g1) // 3, (b0 + 2 * b1) // 3, 255))
            else:
                cols.append(((r0 + r1) // 2, (g0 + g1) // 2, (b0 + b1) // 2, 255))
                cols.append((0, 0, 0, 255))
            if bc3:
                a0, a1 = blk[0], blk[1]
                abits = int.from_bytes(blk[2:8], 'little')
                al = [a0, a1]
                if a0 > a1:
                    for i in range(1, 7):
                        al.append(((7 - i) * a0 + i * a1) // 7)
                else:
                    for i in range(1, 5):
                        al.append(((5 - i) * a0 + i * a1) // 5)
                    al.append(0)
                    al.append(255)
            for j in range(16):
                ci = (bits >> (2 * j)) & 3
                r, g, b, _ = cols[ci]
                if bc3:
                    ai = (abits >> (3 * j)) & 7
                    a = al[ai]
                else:
                    a = 255
                x = bx * 4 + (j % 4)
                y = by * 4 + (j // 4)
                k = (y * W + x) * 4
                px[k:k + 4] = bytes((r, g, b, a))
    return px


def write_png(path, W, H, rgba, scale=1):
    W2, H2 = W * scale, H * scale
    raw = bytearray()
    for y in range(H2):
        raw.append(0)
        sy = y // scale
        row = rgba[sy * W * 4:(sy + 1) * W * 4]
        if scale == 1:
            raw += bytes(row)
        else:
            for x in range(W2):
                sx = x // scale
                raw += bytes(row[sx * 4:sx * 4 + 4])
    # RGBA -> colortype 6
    def chunk(typ, data):
        return struct.pack('>I', len(data)) + typ + data + struct.pack('>I', zlib.crc32(typ + data) & 0xffffffff)
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', W2, H2, 8, 6, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(bytes(raw), 9))
    png += chunk(b'IEND', b'')
    open(path, 'wb').write(png)


if __name__ == '__main__':
    ents = dict(gen(open(PATH, 'rb').read(), 'root'))
    name = sys.argv[1] if len(sys.argv) > 1 else 'root#02428'
    idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    d = ents[name]
    magic, cnt, texs = parse_g1t(d)
    fmt, W, H, data, swz = texs[idx]
    print(f'{name}: magic={magic} texCount={cnt} tex[{idx}] fmt={hex(fmt)} {W}x{H} swz={swz} datalen={len(data)}')
    rgba = decode_dxt(data, W, H, bc3=(fmt in (0x08, 0x12)))
    out = os.path.join(VNTRANS_HOME, f'tmp_c2ff/font_{name.replace("#","_")}_{idx}.png')
    write_png(out, W, H, rgba, scale=4)
    print('->', out)
