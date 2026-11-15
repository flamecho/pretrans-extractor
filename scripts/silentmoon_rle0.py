# -*- coding: utf-8 -*-
"""Silent Moon (Boys3 engine) member codec: 24-byte RLE0 header + payload.

Header (little-endian u32 x5 after 'RLE0'):
  [4] header size (24)
  [8] stored payload size
  [c] decoded size
 [10] method (1 = RLE0 stream, 0 = stored)
 [14] reserved (0)
Decode loop (Boys3.exe 0x4153fc): control byte c; op = c>>6, n = c&0x3f
(n==0 -> 0x40): op0 = literal copy n bytes; op1/2/3 = repeat next 1/2/3-byte
pattern n+1 times.
"""
import struct


def parse_header(buf, off=0):
    if buf[off:off + 4] != b'RLE0':
        raise ValueError('not RLE0')
    hdr_size, stored, decoded, method, rsv = struct.unpack_from('<5I', buf, off + 4)
    return hdr_size, stored, decoded, method, rsv


def rle0_decode(buf, off=0):
    hdr_size, stored, decoded, method, rsv = parse_header(buf, off)
    src = buf[off + hdr_size: off + hdr_size + stored]
    out = bytearray()
    i = 0
    while i < len(src) and len(out) < decoded:
        c = src[i]
        i += 1
        op = c >> 6
        n = c & 0x3f
        if n == 0:
            n = 0x40
        if op == 0:
            out += src[i:i + n]
            i += n
        elif op == 1:
            out += bytes([src[i]]) * (n + 1)
            i += 1
        elif op == 2:
            out += src[i:i + 2] * (n + 1)
            i += 2
        else:
            out += src[i:i + 3] * (n + 1)
            i += 3
    if len(out) != decoded:
        raise ValueError('decoded size mismatch %d != %d' % (len(out), decoded))
    return bytes(out), stored, method


def member_payload(buf, off=0):
    hdr_size, stored, decoded, method, rsv = parse_header(buf, off)
    if method == 1:
        data, _, _ = rle0_decode(buf, off)
        return data
    return buf[off + hdr_size: off + hdr_size + stored]
