#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""：dump NCA 头明文（段表 + 各段 FS 头），供人工判读。"""
import sys
from Crypto.Cipher import AES

MASK = (1 << 128) - 1

def alpha(t):
    c = t >> 127
    t = (t << 1) & MASK
    if c:
        t ^= 0x87
    return t

def xts_dec(k1, k2, data):
    out = bytearray()
    ek2 = AES.new(k2, AES.MODE_ECB)
    dk1 = AES.new(k1, AES.MODE_ECB)
    for s in range(0, len(data), 0x200):
        sec = data[s:s + 0x200]
        tweak = int.from_bytes(ek2.encrypt((s // 0x200).to_bytes(16, 'big')), 'big')
        for j in range(0, len(sec), 0x10):
            blk = sec[j:j + 0x10]
            x = int.from_bytes(blk, 'big') ^ tweak
            p = int.from_bytes(dk1.decrypt(x.to_bytes(16, 'big')), 'big') ^ tweak
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

keys = load_keys(sys.argv[2])
hk = bytes.fromhex(keys['header_key'])
plain = xts_dec(hk[:16], hk[16:], open(sys.argv[1], 'rb').read(0x4000))
print('magic', plain[0x200:0x204], 'keygen', plain[0x206], 'kaek', plain[0x207])
print('dist', plain[0x205], 'ctype', plain[0x204])
for i in range(4):
    e = 0x240 + i * 0x10
    raw = plain[e:e + 0x10]
    print(f'sec{i} raw={raw.hex()}')
    print('   start', hex(int.from_bytes(raw[0:4], "little")), 'end', hex(int.from_bytes(raw[4:8], "little")))
    f = 0x400 + i * 0x200
    print('   fshdr', plain[f:f + 0x20].hex())
    # 找 section_ctr：8B 大端，低 4B 通常是 start/16
    blob = plain[f:f + 0x200]
    for off in range(0, 0x1a0, 4):
        v = blob[off:off + 8]
        if len(v) == 8 and int.from_bytes(v[4:8], 'big') in (0x1c00, 0x8ea5400, 0x1c0, 0x8ea540):
            print('   ctr?@+%#x' % off, v.hex())
