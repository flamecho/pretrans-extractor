"""明治活劇 ハイカラ流星組 (NS-JP) の .lzs 解凍器 (c) 2026.

フォーマット:
    [u32 out_size] + LZSS ストリーム
    - フラグ 1 バイト / 8 トークン, **LSB first**, bit=1 -> リテラル
    - マッチ: 2 バイト [b0][b1]
        len = (b1 & 0x0F) + 3      (3..18)
        off = b0 | ((b1 & 0xF0) << 4)   (0..4095)
    - リングバッファ 4096, **r0 = N - F = 4096 - 18 = 0xFEE**
    - ソース = ring[(off + k) & 0xFFF]   (絶対リング位置)
    - 初期化 0x00 (テキストには影響なし)
"""
import struct, sys, os, glob


def decompress(data):
    out_size = struct.unpack('<I', data[:4])[0]
    s = data[4:]
    ring = bytearray(4096)
    r = 0xFEE
    out = bytearray()
    p = 0
    n = len(s)
    flags = 0
    nb = 0
    while p < n:
        if nb == 0:
            flags = s[p]; p += 1; nb = 8
        bit = (flags >> (8 - nb)) & 1
        nb -= 1
        if bit == 1:
            c = s[p]; p += 1
            out.append(c); ring[r] = c; r = (r + 1) & 0xFFF
        else:
            b0 = s[p]; b1 = s[p + 1]; p += 2
            off = b0 | ((b1 & 0xF0) << 4)
            ln = (b1 & 0x0F) + 3
            for k in range(ln):
                c = ring[(off + k) & 0xFFF]
                out.append(c); ring[r] = c; r = (r + 1) & 0xFFF
    assert len(out) == out_size, (len(out), out_size)
    return bytes(out)


def decompress_file(path, outdir):
    d = open(path, 'rb').read()
    o = decompress(d)
    base = os.path.basename(path)[:-4]  # strip .lzs
    op = os.path.join(outdir, base)
    open(op, 'wb').write(o)
    return op


if __name__ == '__main__':
    src, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    files = sorted(glob.glob(os.path.join(src, '*.lzs')))
    for f in files:
        try:
            decompress_file(f, outdir)
        except Exception as e:
            print('FAIL', f, e)
    print('done', len(files))
