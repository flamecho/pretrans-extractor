import struct, zlib, sys
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
amap = struct.unpack('<%dH' % (len(get(0)) // 2), get(0))
font = get(1)
NG = len(font) // 128
print('codes', len(amap), 'glyphs', NG, file=sys.stderr)

def glyph_pix(g):
    if g >= NG or g < 0: return None
    b = font[g*128:(g+1)*128]
    px = []
    for y in range(16):
        row = []
        for x in range(16):
            byte = b[y*8 + x//2]
            v = (byte >> 4) if x % 2 == 0 else (byte & 0xF)
            row.append(v)
        px.append(row)
    return px

def write_png(path, w, h, gray):
    raw = b''.join(b'\x00' + bytes(gray[y*w:(y+1)*w]) for y in range(h))
    def chunk(t, d):
        c = t + d
        return struct.pack('>I', len(d)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 0, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(raw))
    png += chunk(b'IEND', b'')
    open(path, 'wb').write(png)

def sheet(codes, cols, path, scale=2):
    cw, ch = 16*scale, 16*scale
    n = len(codes)
    r = (n + cols - 1)//cols
    W, H = cols*cw, r*ch
    img = bytearray([255])*(W*H)
    for k, code in enumerate(codes):
        g = amap[code] if code < len(amap) else 0xFFFF
        if g == 0xFFFF: continue
        px = glyph_pix(g)
        if px is None: continue
        cx = (k % cols)*cw; cy = (k//cols)*ch
        for y in range(16):
            for x in range(16):
                v = px[y][x]
                gv = 255 - v*17
                for dy in range(scale):
                    for dx in range(scale):
                        img[(cy+y*scale+dy)*W + cx+x*scale+dx] = gv
    write_png(path, W, H, img)

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'hira':
        sheet(list(range(282, 282+83)), 16, 'hira.png')
    elif mode == 'kata':
        sheet(list(range(376, 376+86)), 16, 'kata.png')
    elif mode == 'range':
        a = int(sys.argv[2]); b = int(sys.argv[3]); cols = int(sys.argv[4]) if len(sys.argv) > 4 else 16
        sheet(list(range(a, b)), cols, 'range.png')
    elif mode == 'ascii':
        sheet(list(range(0x20, 0x7f)), 16, 'ascii.png')
    print('ok', file=sys.stderr)
