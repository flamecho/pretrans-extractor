#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""由 ticket 推 NCA 内容密钥（Titlekey crypto），并用 section 0 的 PFS0/IVFC 魔数自证。
用法: python scripts/tik_key.py <nca> <tik>
输出: 命中的 titlekek 索引 + 16B 内容密钥（供 hactool --titlekey / NCA_KEY=）
"""
import sys, struct
sys.path.insert(0, __file__.rsplit('\\', 1)[0] if '\\' in __file__ else 'tools')
import switch_nca as SN
from Crypto.Cipher import AES
from Crypto.Util import Counter

nca, tikp = sys.argv[1], sys.argv[2]
keys = SN.load_keys('_sw/prod_fixed.keys')
f = open(nca, 'rb')
h = SN.xts_decrypt(bytes.fromhex(keys['header_key'][:32]),
                   bytes.fromhex(keys['header_key'][32:64]), 0, f.read(0x1200))
assert h[0x200:0x204] == b'NCA3', 'NCA3 magic 失败'
secs = [(int.from_bytes(h[0x240 + i * 0x10:0x244 + i * 0x10], 'little') * 0x200,
         int.from_bytes(h[0x244 + i * 0x10:0x248 + i * 0x10], 'little') * 0x200) for i in range(4)]
print('[i] mkr=%#x sections=%s' % (h[0x220], [(hex(a), hex(b)) for a, b in secs if b > a]))
tik = open(tikp, 'rb').read()
enc = tik[0x180:0x190]
print('[i] enc titlekey =', enc.hex().upper())

st, en = secs[0]
for koff in (0x8000, 0):
    for r in range(0x20):
        kk = keys.get('titlekek_%02x' % r)
        if not kk:
            continue
        key = AES.new(bytes.fromhex(kk), AES.MODE_ECB).decrypt(enc)
        iv = (1 << 96) | ((st + koff) // 16)
        f.seek(st + koff)
        b = f.read(16)
        p = AES.new(key, AES.MODE_CTR, counter=Counter.new(128, initial_value=iv)).decrypt(b)
        if p[:4] in (b'PFS0', b'IVFC', b'HFS0'):
            print('[HIT] titlekek_%02x  off=%#x  key=%s  magic=%s' % (r, koff, key.hex(), p[:4].decode()))
            raise SystemExit(0)
print('[!] 未命中：可能 KeyGen 超出 keyset 范围或 tik 与 NCA 不匹配')
