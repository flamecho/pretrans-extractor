#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""：解 NCA 头（AES-XTS header_key），导出各段 FS 头字段（含 section_ctr）。"""
import sys
from Crypto.Cipher import AES

MASK = (1 << 128) - 1

def alpha(t):
    c = t >> 127
    t = (t << 1) & MASK
    if c:
        t ^= 0x87
    return t

def xts_dec(k1, k2, base_sector, data):
    out = bytearray()
    for s in range(0, len(data), 0x200):
        sec = data[s:s + 0x200]
        tweak = int.from_bytes(AES.new(k2, AES.MODE_ECB).encrypt((base_sector + s // 0x200).to_bytes(16, 'big')), 'big')
        for j in range(0, len(sec), 0x10):
            blk = sec[j:j + 0x10]
            x = int.from_bytes(blk, 'big') ^ tweak
            p = int.from_bytes(AES.new(k1, AES.MODE_ECB).decrypt(x.to_bytes(16, 'big')), 'big') ^ tweak
            out += p.to_bytes(16, 'big')
            tweak = alpha(tweak)
    return bytes(out)

def load_keys(path):
    d = {}
    for line in open(path, encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        d[k.strip()] = v.strip()
    return d

keys = load_keys(sys.argv[2] if len(sys.argv) > 2 else '_sw/nofixed.keys')
hdr_key = bytes.fromhex(keys['header_key'])
hdr = open(sys.argv[1], 'rb').read(0x4000)
plain = xts_dec(hdr_key[:16], hdr_key[16:], 0, hdr)
print('magic', plain[0x200:0x204], 'keygen', plain[0x206], 'kaek', plain[0x207])
for i in range(4):
    e = 0x240 + i * 0x10
    ms, me = int.from_bytes(plain[e:e + 4], 'little'), int.from_bytes(plain[e + 4:e + 8], 'little')
    f = 0x400 + i * 0x200
    print(f'sec{i} media_start={hex(ms*0x200)} media_end={hex(me*0x200)} fs_magic={plain[f:f+4]} enc={plain[f+3]} ctr={plain[f+0x140:f+0x148].hex() if False else ""}')
    print('   hdr@0x400:', plain[f:f+0x20].hex())
