#!/usr/bin/env python3
"""OHS 文本段解密：blob 从 0x28 指向处到文件尾，SBOX(0x40..0x140) 递减异或解密"""
import struct


def decrypt_text(d):
    sbox = d[0x40:0x140]
    off = struct.unpack_from('<I', d, 0x28)[0]
    ln = struct.unpack_from('<I', d, 0x14)[0] & 0xFFFF
    if off >= len(d):
        return b'', off
    end = min(len(d), off + ln)
    blob = bytearray(d[off:end])
    t = 0
    for i in range(len(blob)):
        blob[i] = sbox[(t ^ blob[i]) & 0xFF]
        t = (t - 1) & 0xFF
    return bytes(blob), off


def header(d):
    f = struct.unpack_from('<16I', d, 0)
    return {
        'magic': f[0], 'ver': f[1], 'hdr': f[2], 'size': f[3],
        'a_off': f[8], 'b_off': f[9], 't_off': f[10], 't2_off': f[11],
        'packed': f[5], 'cntB': f[6], 'cntA': f[5] >> 16,
    }


if __name__ == '__main__':
    import sys
    for p in sys.argv[1:]:
        d = open(p, 'rb').read()
        blob, off = decrypt_text(d)
        print('==', p, header(d), 'bloblen', len(blob))
