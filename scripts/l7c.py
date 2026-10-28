# -*- coding: utf-8 -*-
"""L7CA (Bandai Namco / Vita resource archive) 解包器。

格式依据 scripts/kuriimu2_src/plugins/BandaiNamco/.../L7c*.cs（onepiecefreak）。
压缩：每文件按 0x10000 分块，块头高字节 0x80=TaikoLz80、0x81=TaikoLz81、0=未压缩。

用法：python scripts/l7c.py <archive.l7c> <outdir> [--list]
"""
import os
import struct
import sys

MASK = 0x7FFF


def taiko80(src, out_size=None):
    """Taiko LZ80（8/16/24bit token，0x8000 环缓）。"""
    buf = bytearray(0x8000)
    pos = 0
    out = bytearray()
    i = 0
    n = len(src)
    while i < n:
        code = src[i]; i += 1
        kind = code >> 6
        if kind == 0:
            length = code & 0x3F
            if code == 0:
                length = 0x40
                b1 = src[i]; i += 1
                if b1 >> 7 == 0:
                    length = 0xBF
                    b2 = src[i]; i += 1
                    if b1 == 0 and b2 == 0:
                        break
                    length += (b1 << 8) | b2
                else:
                    length += b1 & 0x7F
            for _ in range(length):
                b = src[i]; i += 1
                out.append(b)
                buf[pos] = b
                pos = (pos + 1) & MASK
        elif kind == 1:
            length = ((code >> 4) & 0x3) + 2
            disp = (code & 0xF) + 1
            for _ in range(length):
                b = buf[(pos - disp) & MASK]
                out.append(b)
                buf[pos] = b
                pos = (pos + 1) & MASK
        elif kind == 2:
            b1 = src[i]; i += 1
            length = ((code >> 2) & 0xF) + 3
            disp = (((code & 0x3) << 8) | b1) + 1
            for _ in range(length):
                b = buf[(pos - disp) & MASK]
                out.append(b)
                buf[pos] = b
                pos = (pos + 1) & MASK
        else:
            b1 = src[i]; i += 1
            b2 = src[i]; i += 1
            length = (((code & 0x3F) << 1) | (b1 >> 7)) + 4
            disp = (((b1 & 0x7F) << 8) | b2) + 1
            for _ in range(length):
                b = buf[(pos - disp) & MASK]
                out.append(b)
                buf[pos] = b
                pos = (pos + 1) & MASK
    return bytes(out)


class BitReader:
    """LSB-first 位读取器（BitOrder.LeastSignificantBitFirst）。"""
    __slots__ = ('d', 'i', 'bit')

    def __init__(self, data):
        self.d = data
        self.i = 0
        self.bit = 0

    def read_bit(self):
        b = (self.d[self.i] >> self.bit) & 1
        self.bit += 1
        if self.bit == 8:
            self.bit = 0
            self.i += 1
        return b

    def read_bits(self, n):
        v = 0
        for k in range(n):
            v |= self.read_bit() << k
        return v


class Lz81Tree:
    __slots__ = ('children', 'value')

    def __init__(self):
        self.children = [None, None]
        self.value = 0

    @property
    def is_leaf(self):
        return self.children[0] is None

    def build(self, br, value_bits):
        def rec(node):
            if br.read_bit():
                node.children[0] = Lz81Tree()
                rec(node.children[0])
                node.children[1] = Lz81Tree()
                rec(node.children[1])
            else:
                node.value = br.read_bits(value_bits)
        rec(self)

    def read_value(self, br):
        node = self
        while not node.is_leaf:
            node = node.children[br.read_bit()]
        return node.value


COUNTERS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0xa, 0xc, 0xe, 0x10, 0x12, 0x16, 0x1a,
            0x1e, 0x22, 0x2a, 0x32, 0x3a, 0x42, 0x52, 0x62, 0x72, 0x82, 0xa2,
            0xc2, 0xe2, 0x102, 0, 0]
COUNTER_BITS = [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3,
                3, 4, 4, 4, 4, 5, 5, 5, 5, 0, 0, 0]
DISP_RANGES = [1, 2, 3, 4, 5, 7, 9, 0xd, 0x11, 0x19, 0x21, 0x31, 0x41, 0x61,
               0x81, 0xc1, 0x101, 0x181, 0x201, 0x301, 0x401, 0x601, 0x801,
               0xc01, 0x1001, 0x1801, 0x2001, 0x3001, 0x4001, 0x6001, 0, 0]
DISP_BITS = [0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9,
             0xa, 0xa, 0xb, 0xb, 0xc, 0xc, 0xd, 0xd, 0, 0]


def taiko81(src, out_size=None):
    """Taiko LZ81（Huffman 树 + 位流）。"""
    br = BitReader(src)
    initial = br.read_bits(8)
    raw_map = Lz81Tree(); raw_map.build(br, 8)
    idx_map = Lz81Tree(); idx_map.build(br, 6)
    disp_map = Lz81Tree(); disp_map.build(br, 5)

    buf = bytearray(0x8000)
    pos = 0
    out = bytearray()

    def put(bs):
        nonlocal pos
        for b in bs:
            out.append(b)
            buf[pos] = b
            pos = (pos + 1) & MASK

    while True:
        idx = idx_map.read_value(br)
        if idx < 0x20:
            if idx == 0:
                break
            length = COUNTERS[idx]
            if COUNTER_BITS[idx]:
                length += br.read_bits(COUNTER_BITS[idx])
            di = disp_map.read_value(br)
            disp = DISP_RANGES[di]
            if DISP_BITS[di]:
                disp += br.read_bits(DISP_BITS[di])
            if length == 0:
                continue
            put(bytes(buf[(pos - disp) & MASK] for _ in range(length)))
        else:
            cnt = COUNTERS[idx - 0x20]
            if COUNTER_BITS[idx - 0x20]:
                cnt += br.read_bits(COUNTER_BITS[idx - 0x20])
            if cnt == 0:
                continue
            put(bytes(raw_map.read_value(br) for _ in range(cnt)))

    data = bytearray(out)
    if initial >= 3:
        iv = initial - 2
        if len(data) > iv:
            length = len(data) - iv
            p = 0
            while length:
                length -= 1
                data[p + iv] = (data[p] + data[p + iv]) & 0xFF
                p += 1
    return bytes(data)


def read_l7c(path):
    with open(path, 'rb') as f:
        data = f.read()
    magic, unk, arch_size, info_off, info_size, unk2, info_cnt, dir_cnt, \
        file_cnt, chunk_cnt, str_size, unk4 = struct.unpack('<4s11i', data[:48])
    assert magic == b'L7CA', magic
    str_off = len(data) - str_size

    def get_str(off):
        n = data[str_off + off]
        return data[str_off + off + 1:str_off + off + 1 + n].decode('utf-8')

    infos = []
    p = info_off
    for _ in range(info_cnt):
        iid, h, fo, no, ts = struct.unpack('<IiIIq', data[p:p + 24])
        infos.append((iid, h, fo, no, ts))
        p += 24

    files = []
    for _ in range(file_cnt):
        comp, decomp, cidx, ccnt, off, crc = struct.unpack('<5iI', data[p:p + 24])
        files.append(dict(comp=comp, decomp=decomp, chunk=cidx, nchunk=ccnt,
                          off=off, crc=crc))
        p += 24

    chunks = []
    for _ in range(chunk_cnt):
        csize, unk, cid = struct.unpack('<Ihh', data[p:p + 8])
        chunks.append((csize, unk, cid))
        p += 8

    name_by_id = {}
    for iid, h, fo, no, ts in infos:
        if iid < 0:
            continue
        folder = get_str(fo) if fo else ''
        name_by_id[iid] = (folder + '/' + get_str(no)).lstrip('/')
    return data, files, chunks, name_by_id


def decode_file(data, f, chunks):
    start = f['off']
    raw = data[start:start + f['comp']]
    out = bytearray()
    p = 0
    for k in range(f['chunk'] , f['chunk'] + f['nchunk']):
        csize, _unk, _cid = chunks[k]
        flag = (csize >> 24) & 0xFF
        ln = csize & 0xFFFFFF
        seg = raw[p:p + ln]
        p += ln
        if flag == 0x80:
            out += taiko80(seg)
        elif flag == 0x81:
            out += taiko81(seg)
        else:
            out += seg
    return bytes(out[:f['decomp']])


def main():
    arch, outdir = sys.argv[1], sys.argv[2]
    data, files, chunks, names = read_l7c(arch)
    if '--list' in sys.argv:
        for i, f in enumerate(files[:40]):
            csize = chunks[f['chunk']][0]
            print('%4d %-52s comp=%d decomp=%d chunks=%d flag=%02x' %
                  (i, names.get(i, '?'), f['comp'], f['decomp'], f['nchunk'],
                   (csize >> 24) & 0xFF))
        flags = {}
        for f in files:
            for k in range(f['chunk'], f['chunk'] + f['nchunk']):
                flags[(chunks[k][0] >> 24) & 0xFF] = flags.get((chunks[k][0] >> 24) & 0xFF, 0) + 1
        print('chunk flags', flags, 'files', len(files))
        return
    only = None
    for a in sys.argv[3:]:
        if a.startswith('--only='):
            only = a.split('=', 1)[1]
    n = 0
    for i, f in enumerate(files):
        name = names.get(i)
        if not name:
            continue
        if only and only not in name:
            continue
        blob = decode_file(data, f, chunks)
        dst = os.path.join(outdir, name.replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, 'wb') as o:
            o.write(blob)
        n += 1
    print('extracted', n)


if __name__ == '__main__':
    main()
