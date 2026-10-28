#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""：key_area[3] 在所有 KAEK 索引下的试解（16 次，验证 keygen 歧义）。"""
import sys
from Crypto.Cipher import AES
from Crypto.Util import Counter

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
ka_enc = bytes.fromhex('2EF6D80D5AA22B41E6C0A4D7FD80BF26')  # key_area[3] 密文
hi, lo = 0x0000000200000000, 0x1c00
f = open(nca, 'rb')
f.seek(0x1c000)
blob = f.read(0x40)
for i in range(16):
    name = 'key_area_key_application_%02x' % i
    if name not in keys:
        continue
    kek = bytes.fromhex(keys[name])
    k3 = AES.new(kek, AES.MODE_ECB).decrypt(ka_enc)
    p = AES.new(k3, AES.MODE_CTR, counter=Counter.new(128, initial_value=(hi << 64) | lo)).decrypt(blob)
    mark = '<<<' if p[:4] in (b'IVFC', b'ROM0') else ''
    print(i, k3.hex()[:8], p[:8].hex(), mark)
