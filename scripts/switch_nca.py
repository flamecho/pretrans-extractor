#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Switch NCA 解密器（不依赖 hactool）—— 处理 Titlekey crypto / Standard crypto 的 Program NCA。

★ 要点（与 hactool 逐字节一致，2026-10-16 千銃士 Rhodoknight 立）：
  1) NCA 头（0x0..0x1200）用 AES-XTS(header_key) 解。sector tweak = AES_ECB_enc(k2, sector_idx **大端 16B**)，
     同 sector 内每 16B 块 tweak 递进 alpha（GF(2^128)×x，回约 0x87）。NCA3 magic 在 0x200。
  2) 头字段：key_generation @0x206 / key_area_encryption_key_index @0x207；
     rights_id @0x230；段表 @0x240（4×{u32 media_start,u32 media_end,u8 x8}，单位 0x200，小端）；
     段 FS 头 @0x400+secno*0x200（含 magic IVFC/PFS0 与 section_ctr @0x28）。
  3) 段数据 AES-CTR：counter 初值 = 段 FS 头的 section_ctr（低 8B 大端 = 绝对文件偏移/16）。
  4) key area @0x300（4×16B）：i==2 用 titlekey 解，其余用 key_area_key_application[keygen-1] 解。
     Program: section0(exefs) key=key_area[2]，section1(romfs) key=key_area[3]。
  5) Titlekey crypto：`--titlekey` 给 **加密 titlekey（tik[0x180:0x190]）**，
     titlekey = AES_ECB_dec(titlekek[keygen], enc)，其中 keygen = 头部 key_generation。

用法:
  python scripts/switch_nca.py info  <nca> [--keyset=<keys>] [--titlekey=<hex>]
  python scripts/switch_nca.py exefs <nca> <outdir> [--keyset=..] [--titlekey=..]
  python scripts/switch_nca.py romfs <nca> <outdir> [--keyset=..] [--titlekey=..]
  keyset 默认 _sw/prod_fixed.keys；titlekey 缺省时自动去同目录 *.tik 找 rights_id 匹配项。
"""
import sys, os, glob

from Crypto.Cipher import AES
from Crypto.Util import Counter

MASK = (1 << 128) - 1
SECTOR = 0x200


def alpha(T):
    c = T >> 127
    T = (T << 1) & MASK
    if c:
        T ^= 0x87
    return T


def xts_decrypt(k1, k2, base_off, data):
    """AES-XTS 解密（NCA 头）。★ Nintendo 的 tweak 采用**反转字节序**：
    T0 = AES_enc(k2, sector_idx 大端16B)；同 sector 内每 16B 块 T ← rev(α_be(rev(T)))（rev=字节反序）。
    XTS 解密：P = AES_dec(k1, C XOR T) XOR T；data unit = 0x200。
    （2026-10-16 千銃士：由已知明文 hdr.bin 反解 `rev(α_be(rev(T0)))` 全量吻合。）"""
    a1 = AES.new(k1, AES.MODE_ECB)
    a2 = AES.new(k2, AES.MODE_ECB)

    def rev(x):
        return int.from_bytes(x.to_bytes(16, 'big'), 'little')

    out = bytearray()
    nsect = len(data) // SECTOR + (1 if len(data) % SECTOR else 0)
    for s in range(nsect):
        sec_idx = (base_off + s * SECTOR) // SECTOR
        T = int.from_bytes(a2.encrypt(sec_idx.to_bytes(16, 'big')), 'big')
        chunk = data[s * SECTOR:(s + 1) * SECTOR]
        for b in range(len(chunk) // 16):
            blk = chunk[b * 16:b * 16 + 16]
            tb = T.to_bytes(16, 'big')
            p = a1.decrypt(bytes(x ^ y for x, y in zip(blk, tb)))
            out += bytes(m ^ n for m, n in zip(p, tb))
            T = rev(alpha(rev(T)))
    return bytes(out)


def ctr_decrypt(key, section_ctr, base_low8, offset_in_sec, data):
    """AES-CTR：counter = section_ctr，低 8B = base_low8 + offset_in_sec/16（大端）。"""
    lo = (base_low8 + offset_in_sec // 16) & ((1 << 64) - 1)
    ctr = section_ctr[:8] + lo.to_bytes(8, 'big')
    return AES.new(key, AES.MODE_CTR, counter=Counter.new(128, initial_value=int.from_bytes(ctr, 'big'))).decrypt(data)


def load_keys(path):
    d = {}
    for line in open(path, encoding='utf-8', errors='ignore'):
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            d[k.strip()] = v.strip()
    return d


def find_titlekey(nca_path, keys):
    """同目录 *.tik 中 rights_id 匹配项 → 用 titlekek 解出 titlekey。"""
    d = open(nca_path, 'rb').read(0x400)
    rights = d[0x230:0x240]
    for tik in glob.glob(os.path.join(os.path.dirname(nca_path), '*.tik')):
        t = open(tik, 'rb').read()
        if t[0x2A0:0x2B0] == rights:
            enc = t[0x180:0x190]
            return enc, rights
    return None, rights


def parse(nca_path, keyset, titlekey_hex):
    f = open(nca_path, 'rb')
    hdr = xts_decrypt(bytes.fromhex(keyset['header_key'][:32]),
                      bytes.fromhex(keyset['header_key'][32:64]), 0, f.read(0x1200))
    assert hdr[0x200:0x204] == b'NCA3', 'header magic != NCA3'
    keygen = hdr[0x206]
    kaek = hdr[0x207]
    rights = hdr[0x230:0x240]
    enc_type = None
    # section table
    secs = []
    for i in range(4):
        e = hdr[0x240 + i * 0x10:0x240 + i * 0x10 + 0x10]
        ms = int.from_bytes(e[0:4], 'little')
        me = int.from_bytes(e[4:8], 'little')
        secs.append((ms * 0x200, me * 0x200))
    # key area
    ka = hdr[0x300:0x340]
    key_area_key = bytes.fromhex(keyset['key_area_key_application_%02x' % (keygen - 1)])
    dec = []
    for i in range(4):
        blk = ka[i * 16:i * 16 + 16]
        if i == 2 and titlekey_hex:
            tk = bytes.fromhex(titlekey_hex)
            dec.append(AES.new(tk, AES.MODE_ECB).decrypt(blk))
        else:
            dec.append(AES.new(key_area_key, AES.MODE_ECB).decrypt(blk))
    # fs headers (decrypted region)
    fsinfo = []
    for i in range(4):
        fh = hdr[0x400 + i * 0x200:0x400 + i * 0x200 + 0x200]
        magic = fh[0x20:0x24]
        ctr = fh[0x28:0x38]
        fsinfo.append((magic, ctr))
    return f, hdr, keygen, secs, dec, fsinfo


def main():
    if len(sys.argv) < 3:
        print(__doc__); return
    cmd = sys.argv[1]
    nca = sys.argv[2]
    keyset_path = '_sw/prod_fixed.keys'
    titlekey_hex = None
    for a in sys.argv[3:]:
        if a.startswith('--keyset='):
            keyset_path = a.split('=', 1)[1]
        elif a.startswith('--titlekey='):
            titlekey_hex = a.split('=', 1)[1]
    keys = load_keys(keyset_path)
    if not titlekey_hex:
        enc, rights = find_titlekey(nca, keys)
        if enc:
            hdr0 = xts_decrypt(bytes.fromhex(keys['header_key'][:32]),
                               bytes.fromhex(keys['header_key'][32:64]), 0, open(nca, 'rb').read(0x1200))
            kg = hdr0[0x206]
            titlekey_hex = AES.new(bytes.fromhex(keys['titlekek_%02x' % kg]), AES.MODE_ECB).decrypt(enc).hex()
            print('[i] titlekey auto: enc=%s → %s (keygen %d)' % (enc.hex(), titlekey_hex, kg))
    f, hdr, keygen, secs, ka, fsinfo = parse(nca, keys, titlekey_hex)
    print('[i] keygen=%d kaek=%d' % (keygen, hdr[0x207]))
    for i, (magic, ctr) in enumerate(fsinfo):
        print('  sec%d magic=%s offset=0x%x size=0x%x ctr=%s' % (i, magic, secs[i][0], secs[i][1] - secs[i][0], ctr.hex()))

    if cmd == 'info':
        return
    outdir = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else '.'
    if cmd == 'exefs':
        secno, keyidx = 0, 2
    elif cmd == 'romfs':
        secno, keyidx = 1, 3
    else:
        print('unknown cmd'); return
    os.makedirs(outdir, exist_ok=True)
    sec_off, sec_end = secs[secno]
    _, ctr = fsinfo[secno]
    base_low8 = int.from_bytes(ctr[8:16], 'big')
    key = ka[keyidx]
    # section 0 = PFS0（exefs）: 前 0x800 是 PFS0 头；section1 = IVFC（romfs）
    size = sec_end - sec_off
    step = 1 << 20
    pos = 0
    buf = bytearray()
    while pos < size:
        n = min(step, size - pos)
        f.seek(sec_off + pos)
        raw = f.read(n)
        buf += ctr_decrypt(key, ctr, base_low8, pos, raw)
        pos += n
    open(os.path.join(outdir, '_decrypted.bin'), 'wb').write(buf)
    print('[+] wrote %s (%d bytes)  head=%s' % (os.path.join(outdir, '_decrypted.bin'), len(buf), bytes(buf[:16])))


if __name__ == '__main__':
    main()
