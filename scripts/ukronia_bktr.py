#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""：BKTR 段（enc=3）解密试验。key_area[3] 用 KAEK[keygen-1] 解，再试 romfs 解密。"""
import sys
from Crypto.Cipher import AES
from Crypto.Util import Counter

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
            x = int.from_bytes(sec[j:j + 0x10], 'big') ^ tweak
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

nca = sys.argv[1]
keys = load_keys(sys.argv[2])
hk = bytes.fromhex(keys['header_key'])
plain = xts_dec(hk[:16], hk[16:], open(nca, 'rb').read(0x4000))
kg = plain[0x206]
print('keygen', kg, 'kaek', plain[0x207])
kaek = bytes.fromhex(keys['key_area_key_application_%02x' % (kg - 1)])
ka = plain[0x300:0x340]
print('key_area enc:', [ka[i * 16:i * 16 + 16].hex() for i in range(4)])
ka3 = AES.new(kaek, AES.MODE_ECB).decrypt(ka[0x30:0x40])
print('ka3 =', ka3.hex())
print('sec1 fshdr:', plain[0x600:0x660].hex())
f = open(nca, 'rb')
for lo in (0x1c00, 0, 0x1c00 + 0x1c0, 0x1c00 - 0x1c0):
    for hi in (0x0000000200000000, 0, 0x0000000002000000):
        f.seek(0x1c000)
        d = f.read(0x100)
        init = ((hi << 64) | lo) & ((1 << 128) - 1)
        p = AES.new(ka3, AES.MODE_CTR, counter=Counter.new(128, initial_value=init)).decrypt(d)
        print('lo=%#x hi=%#x' % (lo, hi), p[:4].hex(), p[:16])
