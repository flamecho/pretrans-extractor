#!/usr/bin/env python3
"""chd_iso.py —— CHD v5 (zstd/lzma/none) -> 2048B/扇区裸 ISO，无 chdman 依赖。

用法:
  python scripts/chd_iso.py <in.chd> <out.iso> [--no-sha1]

自证:
  1) map 解出结果 CRC16 == map 头 mapcrc
  2) 整盘 SHA1 == 头部 rawsha1（--no-sha1 可跳，默认做）
  3) 逻辑偏移 0x8000 == \\x01CD001，且根目录含 PSP_GAME

实现依据 MAME src/lib/util/chd.cpp（v5）：
  hunk map = Huffman(16 codes, maxbits 8, 码长位宽 4bit, RLE 导入) 类型流 + 位流参数两遍。
"""
import hashlib
import struct
import sys

import zstandard as zstd

HUFF_COMP_0, HUFF_COMP_3 = 0, 3
HUFF_NONE, HUFF_SELF, HUFF_PARENT = 4, 5, 6
HUFF_RLE_SMALL, HUFF_RLE_LARGE = 7, 8
HUFF_SELF_0, HUFF_SELF_1 = 9, 10
HUFF_PARENT_SELF, HUFF_PARENT_0, HUFF_PARENT_1 = 11, 12, 13

CRC_TBL = []
for _i in range(256):
    _c = _i << 8
    for _ in range(8):
        _c = ((_c << 1) ^ 0x1021) & 0xFFFF if _c & 0x8000 else (_c << 1) & 0xFFFF
    CRC_TBL.append(_c)


def crc16(buf, init=0xFFFF):
    c = init
    for b in buf:
        c = ((c << 8) & 0xFFFF) ^ CRC_TBL[((c >> 8) ^ b) & 0xFF]
    return c


class BitReader:
    """MSB-first 位流。"""
    __slots__ = ('b', 'pos')

    def __init__(self, buf):
        self.b = buf
        self.pos = 0

    def peek(self, n):
        v = 0
        p = self.pos
        for i in range(n):
            q = p + i
            v = (v << 1) | ((self.b[q >> 3] >> (7 - (q & 7))) & 1)
        return v

    def read(self, n):
        v = self.peek(n)
        self.pos += n
        return v

    def remove(self, n):
        self.pos += n


def build_huffman(buf, numcodes=16, maxbits=8, lenbits=4):
    """huffman_import_tree_rle + 规范化码 + 1<<maxbits 查表。返回 (lut, consumed_bitpos)。"""
    br = BitReader(buf)
    lens = [0] * numcodes
    cur = 0
    while cur < numcodes:
        v = br.read(lenbits)
        if v != 1:
            lens[cur] = v
            cur += 1
        else:
            v = br.read(lenbits)
            if v == 1:
                lens[cur] = 1
                cur += 1
            else:
                rep = br.read(lenbits) + 3
                while rep > 0 and cur < numcodes:
                    lens[cur] = v
                    cur += 1
                    rep -= 1
    kraft = sum(2.0 ** -l for l in lens if l)
    if abs(kraft - 1.0) > 1e-9:
        raise SystemExit('huffman tree invalid: Kraft sum=%.6f' % kraft)

    hist = [0] * 34
    for l in lens:
        hist[l] += 1
    curstart = 0
    for codelen in range(32, 0, -1):
        nxt = (curstart + hist[codelen]) >> 1
        hist[codelen] = curstart
        curstart = nxt
    codes = [0] * numcodes
    for i in range(numcodes):
        if lens[i]:
            codes[i] = hist[lens[i]]
            hist[lens[i]] += 1

    lut = [-1] * (1 << maxbits)
    for c in range(numcodes):
        n = lens[c]
        if not n:
            continue
        shift = maxbits - n
        for i in range(codes[c] << shift, (codes[c] + 1) << shift):
            if i < len(lut):
                lut[i] = (c << 5) | n
    return lut, br.pos


def decode_map(f, mapoffset, hunkcount, hunkbytes, unitbytes, has_parent):
    f.seek(mapoffset)
    mh = f.read(16)
    mapbytes, firstoffs, mapcrc = struct.unpack_from('>I', mh, 0)[0], int.from_bytes(mh[4:10], 'big'), struct.unpack_from('>H', mh, 10)[0]
    lengthbits, selfbits, parentbits = mh[12], mh[13], mh[14]
    f.seek(mapoffset + 16)
    mz = f.read(mapbytes)
    if len(mz) != mapbytes:
        raise SystemExit('map stream truncated')

    lut, pos = build_huffman(mz)
    br = BitReader(mz)
    br.pos = pos

    def dec():
        e = lut[br.peek(8)]
        if e < 0:
            raise SystemExit('huffman LUT miss @bit %d' % br.pos)
        br.remove(e & 31)
        return e >> 5

    # ---- Pass 1: 类型 ----
    types = bytearray(hunkcount)
    lastcomp, repeat = 0, 0
    for i in range(hunkcount):
        if repeat:
            types[i] = lastcomp
            repeat -= 1
            continue
        t = dec()
        # RLE 只带「重复计数」一个符号，类型沿用上一个（v5 实测：2 独立判据互证）
        if t == HUFF_RLE_SMALL:
            repeat = 2 + dec()
            t = lastcomp
        elif t == HUFF_RLE_LARGE:
            repeat = 2 + 16 + (dec() << 4) + dec()
            t = lastcomp
        else:
            lastcomp = t
        types[i] = t

    # ---- Pass 2: length / offset / crc ----
    entries = []
    curoffset, last_self, last_parent = firstoffs, 0, 0
    for i in range(hunkcount):
        t = types[i]
        offset, length, crc = curoffset, 0, 0
        if t <= HUFF_COMP_3:
            length = br.read(lengthbits)
            curoffset += length
            crc = br.read(16)
        elif t == HUFF_NONE:
            length = hunkbytes
            curoffset += length
            crc = br.read(16)
        elif t == HUFF_SELF:
            last_self = offset = br.read(selfbits)
        elif t == HUFF_PARENT:
            last_parent = offset = br.read(parentbits)
        elif t == HUFF_SELF_0:
            t = HUFF_SELF
            offset = last_self
        elif t == HUFF_SELF_1:
            t = HUFF_SELF
            last_self += 1
            offset = last_self
        elif t == HUFF_PARENT_SELF:
            t = HUFF_PARENT
            last_parent = offset = (i * hunkbytes) // unitbytes
        elif t == HUFF_PARENT_0:
            t = HUFF_PARENT
            offset = last_parent
        elif t == HUFF_PARENT_1:
            t = HUFF_PARENT
            last_parent += hunkbytes // unitbytes
            offset = last_parent
        if t == HUFF_PARENT and not has_parent:
            raise SystemExit('PARENT hunk @%d but no parent' % i)
        entries.append((t, length, offset, crc))

    # mapcrc 覆盖的就是这 12B×N 的序列化
    raw = bytearray(hunkcount * 12)
    for i, (t, length, offset, crc) in enumerate(entries):
        raw[i * 12] = t
        raw[i * 12 + 1:i * 12 + 4] = length.to_bytes(3, 'big')
        raw[i * 12 + 4:i * 12 + 10] = offset.to_bytes(6, 'big')
        raw[i * 12 + 10:i * 12 + 12] = crc.to_bytes(2, 'big')
    got = crc16(raw)
    if got != mapcrc:
        raise SystemExit('mapcrc mismatch: got %04x want %04x' % (got, mapcrc))
    return entries


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    src, dst = sys.argv[1], sys.argv[2]
    do_sha1 = '--no-sha1' not in sys.argv

    f = open(src, 'rb')
    hdr = f.read(124)
    if hdr[:8] != b'MComprHD':
        raise SystemExit('not a CHD: %r' % hdr[:8])
    hdrlen, version = struct.unpack_from('>I', hdr, 8)[0], struct.unpack_from('>I', hdr, 12)[0]
    if version != 5:
        raise SystemExit('only CHD v5 supported (got v%d)' % version)
    comps = [hdr[16 + 4 * i:20 + 4 * i].decode('latin1').strip('\0 ') for i in range(4)]
    logical = int.from_bytes(hdr[32:40], 'big')
    mapoffset = int.from_bytes(hdr[40:48], 'big')
    metaoffset = int.from_bytes(hdr[48:56], 'big')
    hunkbytes, unitbytes = struct.unpack_from('>II', hdr, 56)
    rawsha1 = hdr[64:84]
    has_parent = any(hdr[104 + i] for i in range(20))
    hunkcount = logical // hunkbytes

    print('hdr_len=%d ver=%d comp=%s logical=%d hunk=%d unit=%d hunks=%d map@0x%x meta@0x%x'
          % (hdrlen, version, comps, logical, hunkbytes, unitbytes, hunkcount, mapoffset, metaoffset))

    entries = decode_map(f, mapoffset, hunkcount, hunkbytes, unitbytes, has_parent)

    zdec = zstd.ZstdDecompressor()
    sha = hashlib.sha1() if do_sha1 else None
    out = open(dst, 'w+b')
    crcbad = 0
    n_self = 0
    i = 0
    types_hist = {}
    while i < hunkcount:
        t, length, offset, crc = entries[i]
        types_hist[t] = types_hist.get(t, 0) + 1
        if t == HUFF_NONE:
            # 合并连续的 NONE（压缩档里通常是整段裸数据）
            j, off = i, offset
            while j < hunkcount and entries[j][0] == HUFF_NONE and entries[j][2] == off:
                off += hunkbytes
                j += 1
            n = (j - i) * hunkbytes
            f.seek(offset)
            left = n
            while left:
                chunk = f.read(min(left, 1 << 22))
                if not chunk:
                    raise SystemExit('source EOF @hunk %d' % i)
                out.write(chunk)
                if sha:
                    sha.update(chunk)
                left -= len(chunk)
            i = j
            continue
        if t <= HUFF_COMP_3:
            f.seek(offset)
            comp = f.read(length)
            name = comps[t]
            if name == 'zstd':
                data = zdec.decompress(comp, max_output_size=hunkbytes)
            elif name == 'none':
                data = comp
            elif name == 'lzma':
                import lzma
                props = comp[0]
                lc, lp, pb = props % 9, (props // 9) % 5, props // 45
                dictsz = struct.unpack_from('<I', comp, 1)[0]
                filt = [{'id': lzma.FILTER_LZMA1, 'lc': lc, 'lp': lp, 'pb': pb, 'dict_size': dictsz}]
                data = lzma.LZMADecompressor(lzma.FORMAT_RAW, filters=filt).decompress(comp[5:], max_length=hunkbytes)
            else:
                raise SystemExit('unsupported compressor %r' % name)
            if len(data) != hunkbytes:
                raise SystemExit('hunk %d len %d != %d' % (i, len(data), hunkbytes))
        elif t == HUFF_SELF:
            srcpos = offset * unitbytes
            out.flush()
            if srcpos + hunkbytes > i * hunkbytes:
                raise SystemExit('SELF forward ref @hunk %d' % i)
            rfd = open(dst, 'rb')
            rfd.seek(srcpos)
            data = rfd.read(hunkbytes)
            rfd.close()
            n_self += 1
        else:
            raise SystemExit('unsupported hunk type %d @%d' % (t, i))
        if crc and crc16(data) != crc:
            crcbad += 1
        out.write(data)
        if sha:
            sha.update(data)
        i += 1

    out.flush()
    out.close()
    f.close()
    print('hunk types %s  self=%d  crcbad=%d' % (types_hist, n_self, crcbad))
    if sha:
        d = sha.hexdigest()
        ok = d == rawsha1.hex()
        print('sha1 %s  hdr %s  => %s' % (d, rawsha1.hex(), 'OK' if ok else 'MISMATCH'))
        if not ok:
            raise SystemExit('rawsha1 mismatch')

    # 结构自证
    f = open(dst, 'rb')
    f.seek(0x8000)
    pvd = f.read(2048)
    if pvd[1:6] != b'CD001':
        raise SystemExit('no CD001 at 0x8000: %r' % pvd[:8])
    root_lba = struct.unpack_from('<I', pvd, 156 + 2)[0]
    root_size = struct.unpack_from('<I', pvd, 156 + 10)[0]
    f.seek(root_lba * 2048)
    root = f.read(root_size)
    names = []
    p = 0
    while p < len(root):
        ln = root[p]
        if ln == 0:
            p = (p // 2048 + 1) * 2048
            continue
        nl = root[p + 32]
        names.append(root[p + 33:p + 33 + nl].decode('latin1').split(';')[0])
        p += ln
    f.close()
    print('root entries:', names)
    if 'PSP_GAME' not in names:
        raise SystemExit('PSP_GAME not in root')
    print('OK ->', dst)
    return 0


if __name__ == '__main__':
    sys.exit(main())
