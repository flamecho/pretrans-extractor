#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""三国恋戦記 魁 (Daisy2 / sgs_*.dat, DDP2/DDP3) 解包 + 解密 + 解压"""
import struct, re, sys, os

MAG = b'\x44\x44\x57\x75\x48\x58\x42'  # "DDWuHXB" inner magic

def lz_decode(src, outsize):
    """自定义 LZSS (见 exe 0x4226c0)"""
    out = bytearray(); i = 0; n = len(src)
    while len(out) < outsize:
        c = src[i]; i += 1
        if c < 0x1d:
            ln = c + 1; out += src[i:i+ln]; i += ln
        elif c == 0x1d:
            ln = src[i] + 0x1e; i += 1; out += src[i:i+ln]; i += ln
        elif c == 0x1e:
            ln = (src[i] << 8 | src[i+1]) + 0x11e; i += 2; out += src[i:i+ln]; i += ln
        elif c == 0x1f:
            ln = (src[i] << 24 | src[i+1] << 16 | src[i+2] << 8 | src[i+3]); i += 4; out += src[i:i+ln]; i += ln
        else:
            if c < 0x40:
                dist = (c >> 2) & 7; ln = (c & 3) + 3
            elif c < 0x60:
                dist = src[i]; i += 1; ln = (c & 0x1f) + 7
            elif c < 0x80:
                dist = ((c & 0x1f) << 8) | src[i]; i += 1; L = src[i]; i += 1
                if L == 0xfe:
                    ln = (src[i] << 8 | src[i+1]) + 0x105; i += 2
                elif L == 0xff:
                    ln = (src[i] << 24 | src[i+1] << 16 | src[i+2] << 8 | src[i+3]) + 3; i += 4
                else:
                    ln = L + 7
            else:
                dist = ((c & 0x1f) << 8) | src[i]; i += 1; ln = ((c >> 5) & 3) + 3
            st = len(out) - dist - 1
            for k in range(ln):
                out.append(out[st + k])
    return bytes(out), i

def make_key(size):
    """见 exe 0x40ff50：key = ((size<<5)^0xA5) * (size+0x6F349) ^ 0x34A9B129 (32bit)"""
    k = ((size << 5) & 0xffffffff) ^ 0xa5
    k = (k * ((size + 0x6f349) & 0xffffffff)) & 0xffffffff
    return k ^ 0x34a9b129

def decrypt_block(inner, size):
    """内层文件 = 16B 头 + payload；payload 按 DWORD XOR 大小派生密钥"""
    key = make_key(size)
    pay = bytearray(inner[16:])
    for off in range(0, (len(pay)//4)*4, 4):
        v = struct.unpack_from('<I', pay, off)[0] ^ key
        struct.pack_into('<I', pay, off, v)
    return bytes(pay), key

def parse_ddp(path, verbose=False):
    """返回 [(name, data_offset, outsize, stored)]；stored==0 表示未压缩"""
    d = open(path, 'rb').read()
    magic = d[:4]
    entries = []
    if magic == b'DDP2':
        cnt, doff = struct.unpack_from('<II', d, 4)
        for i in range(cnt):
            off, full, stored, _ = struct.unpack_from('<IIII', d, 0x20 + i*16)
            entries.append((None, off, full, stored))
        return d, entries, 'DDP2'
    if magic != b'DDP3':
        raise ValueError('not DDP: %r' % magic)
    # DDP3: 块由 inner magic 定位；记录在 [0x120, data_off) 区间
    data_off = struct.unpack_from('<I', d, 8)[0]
    starts = [m.start()-2 for m in re.finditer(re.escape(MAG), d)]
    def find_rec(off):
        for p in range(0x20, data_off):
            if p+0x13 <= len(d) and d[p] > 0 and d[p+1:p+5] == struct.pack('<I', off):
                ln = d[p]
                nm = d[p+0x11:p+0x11+ln-0x13].decode('utf-16le', 'replace')
                return nm, struct.unpack_from('<I', d, p+5)[0], struct.unpack_from('<I', d, p+9)[0]
        return None
    for off in starts:
        r = find_rec(off)
        if r:
            entries.append((r[0], off, r[1], r[2]))
        else:
            # 兜底：从相邻推断 outsize/stored
            entries.append((None, off, None, None))
    return d, entries, 'DDP3'

def get_block(d, off, outsize, stored):
    """取出并解密一个块 -> 明文(内层 payload)。返回 (plaintext, inner)"""
    if stored == 0:
        raw = d[off:off+outsize]
        return raw, raw
    blk = d[off:off+stored]
    inner, _ = lz_decode(blk, outsize)
    assert inner[:7] == MAG, 'inner magic mismatch at %x' % off
    plain, _ = decrypt_block(inner, outsize)
    return plain, inner

if __name__ == '__main__':
    for path in sys.argv[1:]:
        d, entries, typ = parse_ddp(path)
        print('==', path, typ, len(entries), 'entries')
        for nm, off, osz, st in entries:
            print('   %-24s off=%#x out=%s stored=%s' % (nm, off, osz, st))
