#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NCA 头/key area 检视器（Switch）—— 用于旧 hactool 无法处理的 BKTR 增量补丁 NCA。

★ 已证实要点（OZMAFIA!! -vivace- 1.0.1 补丁，2026-10-12）：
  1) NCA 头 XTS 解密：sector tweak = AES_enc(header_key[16:], sector_idx **大端 16B**)，
     同一 sector 内每 16B 块 tweak 递进 alpha（GF(2^128) ×x，回约 0x87）。
     （`NCA3` magic 在 0x200，不是 0x0；0x200 之前是 RSA/固定键签名）
  2) 段表 @0x240：u32 **小端**，单位 0x200（media_start, media_end）×4 段。
     rights_id @0x230（16B）；key_generation @0x206 / key_generation_2 @0x220 ⇒ keygen = max−1。
  3) 段数据 AES-CTR：counter 初值 = 段表 FS 头的 section_ctr（bytes[0:4]=段号+1，bytes[8:16]=段文件偏移/16，大端 16B）。
     ⚠ 用 decrypted-titlekey 直接解本补丁段**不成立**（key area 全 0）⇒ 本工具尚未解决内容密钥。

用法:
  python scripts/ozmafia_nca.py info <nca>     # 打印头字段 / 段表 / key area
  python scripts/ozmafia_nca.py ctr  <nca> <secno>   # 打印该段 section_ctr 与文件偏移
"""
import sys, os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

try:
    from Crypto.Cipher import AES
except ImportError:
    AES = None

MASK = (1 << 128) - 1


def alpha(T):
    c = T >> 127
    T = (T << 1) & MASK
    return T ^ 0x87 if c else T


def xts_dec(data, key, base_sector=0):
    """NCA 头/key area 用 XTS（sector tweak = AES(k2, sector 大端 16B)，块间 alpha 递进）。"""
    k1, k2 = key[:16], key[16:]
    ea, eb = AES.new(k1, AES.MODE_ECB), AES.new(k2, AES.MODE_ECB)
    out = bytearray()
    for s in range(0, len(data), 0x200):
        sec = data[s:s + 0x200]
        T = int.from_bytes(eb.encrypt((base_sector + s // 0x200).to_bytes(16, 'big')), 'little')
        for j in range(0, len(sec), 16):
            blk = sec[j:j + 16].ljust(16, b'\x00')
            p = ea.decrypt((int.from_bytes(blk, 'little') ^ T).to_bytes(16, 'little'))
            out += (int.from_bytes(p, 'little') ^ T).to_bytes(16, 'little')
            T = alpha(T)
    return bytes(out)


def load_keys(paths):
    d = {}
    for p in paths:
        if not os.path.exists(p):
            continue
        for line in open(p, encoding='utf-8', errors='replace'):
            s = line.strip()
            if '=' not in s:
                continue
            k, v = [x.strip() for x in s.split('=', 1)]
            v = v.replace('0x', '')
            if len(v) in (32, 64):
                try:
                    d[k] = bytes.fromhex(v)
                except ValueError:
                    pass
    return d


def parse_header(nca, keys):
    raw = open(nca, 'rb').read(0x400)
    hdr = xts_dec(raw, keys['header_key'])
    assert hdr[0x200:0x204] == b'NCA3', 'header decrypt failed: %r' % hdr[0x200:0x204]
    return hdr


def sections(hdr):
    out = []
    for i in range(4):
        b = 0x240 + i * 0x10
        start = int.from_bytes(hdr[b:b + 4], 'little') * 0x200
        end = int.from_bytes(hdr[b + 4:b + 8], 'little') * 0x200
        out.append((start, end - start))
    return out


def main():
    if AES is None:
        sys.exit('need pycryptodome')
    cmd, nca = sys.argv[1], sys.argv[2]
    keys = load_keys([os.path.join(VNTRANS_HOME, '_sw/keys.txt'), os.path.join(VNTRANS_HOME, '<你的 prod.keys>')])
    hdr = parse_header(nca, keys)
    kg = max(hdr[0x206], hdr[0x220])
    print('magic=%s version=%#x keygen=%d rights_id=%s' %
          (hdr[0x200:0x204].decode('ascii', 'replace'), int.from_bytes(hdr[0x204:0x208], 'big'),
           kg, hdr[0x230:0x240].hex()))
    for i, (s, n) in enumerate(sections(hdr)):
        if n:
            print('  section%d: off=%#x size=%#x  ctr=%s' %
                  (i, s, n, (bytes([0, 0, 0, i + 1]) + b'\x00' * 4 + (s >> 4).to_bytes(8, 'big')).hex()))
    if cmd == 'info':
        print('  key area @0x300:', hdr[0x300:0x340].hex())


if __name__ == '__main__':
    main()
