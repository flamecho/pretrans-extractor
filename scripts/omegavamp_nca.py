#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""オメガヴァンパイア(NS) 专用 NCA/RomFS 按需解密提取器（不改共用 scripts/switch_nca.py）。

用法:
  python scripts/omegavamp_nca.py info   <nca> <tik>
  python scripts/omegavamp_nca.py list   <nca> <tik> [--substr=PAK]
  python scripts/omegavamp_nca.py get    <nca> <tik> <romfs 虚拟路径如 /1/SCRIPT.PAK> <输出文件>
"""
import sys, os, struct
from Crypto.Cipher import AES
from Crypto.Util import Counter

MASK = (1 << 128) - 1
SECTOR = 0x200
KEYS = '_sw/prod_fixed.keys'


def alpha(T):
    c = T >> 127
    T = (T << 1) & MASK
    if c:
        T ^= 0x87
    return T


def xts_decrypt(k1, k2, base_off, data):
    a1 = AES.new(k1, AES.MODE_ECB)
    a2 = AES.new(k2, AES.MODE_ECB)

    def rev(x):
        return int.from_bytes(x.to_bytes(16, 'big'), 'little')

    out = bytearray()
    for s in range(len(data) // SECTOR + (1 if len(data) % SECTOR else 0)):
        T = int.from_bytes(a2.encrypt(((base_off + s * SECTOR) // SECTOR).to_bytes(16, 'big')), 'big')
        chunk = data[s * SECTOR:(s + 1) * SECTOR]
        for b in range(len(chunk) // 16):
            tb = T.to_bytes(16, 'big')
            p = a1.decrypt(bytes(x ^ y for x, y in zip(chunk[b * 16:b * 16 + 16], tb)))
            out += bytes(m ^ n for m, n in zip(p, tb))
            T = rev(alpha(rev(T)))
    return bytes(out)


def load_keys(path=KEYS):
    d = {}
    for line in open(path, encoding='utf-8', errors='ignore'):
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            d[k.strip()] = v.strip()
    return d


class Nca:
    def __init__(self, path, tik):
        self.f = open(path, 'rb')
        self.keys = load_keys()
        hk = self.keys['header_key']
        hdr = xts_decrypt(bytes.fromhex(hk[:32]), bytes.fromhex(hk[32:64]), 0, self.f.read(0x1200))
        assert hdr[0x200:0x204] == b'NCA3', hdr[0x200:0x204]
        self.hdr = hdr
        self.keygen = hdr[0x206]
        t = open(tik, 'rb').read()
        enc_tk = t[0x180:0x190]
        self.titlekey = AES.new(bytes.fromhex(self.keys['titlekek_%02x' % self.keygen]),
                                AES.MODE_ECB).decrypt(enc_tk)
        ka = hdr[0x300:0x340]
        kak = bytes.fromhex(self.keys['key_area_key_application_%02x' % (self.keygen - 1)])
        self.ka = []
        for i in range(4):
            blk = ka[i * 16:i * 16 + 16]
            if i == 2:
                self.ka.append(AES.new(self.titlekey, AES.MODE_ECB).decrypt(blk))
            else:
                self.ka.append(AES.new(kak, AES.MODE_ECB).decrypt(blk))
        secs = []
        for i in range(4):
            e = hdr[0x240 + i * 0x10:0x250 + i * 0x10]
            ms = int.from_bytes(e[0:4], 'little')
            me = int.from_bytes(e[4:8], 'little')
            secs.append((ms * 0x200, me * 0x200))
        self.secs = secs
        fh = hdr[0x400 + 0x200:0x400 + 0x400]          # section1 = romfs
        self.ctr = fh[0x28:0x38]
        self.rom_base, self.rom_end = secs[1]
        self.key = self.ka[3]
        self.iv = int.from_bytes(self.ctr[8:16], 'big')

    def read(self, off, n):
        """读 romfs section 内 [off, off+n) 的明文。"""
        self.f.seek(self.rom_base + off)
        raw = self.f.read(n)
        ctr = self.ctr[:8] + ((self.iv + off // 16) & ((1 << 64) - 1)).to_bytes(8, 'big')
        return AES.new(self.key, AES.MODE_CTR,
                       counter=Counter.new(128, initial_value=int.from_bytes(ctr, 'big'))).decrypt(raw)


def parse_romfs(nca):
    head = nca.read(0, 0x100)
    (hsize, dh_off, dh_size, fh_off, fh_size,
     ft_off, ft_size, dt_off, dt_size) = struct.unpack('<9Q', head[:0x48])
    base = 0x8cc000                                    # IVFC data layer
    ft = nca.read(base + ft_off, ft_size)
    dt = nca.read(base + dt_off, dt_size)
    files = []
    for i in range(len(ft) // 0x20):
        e = ft[i * 0x20:(i + 1) * 0x20]
        parent, sib, off, size = struct.unpack('<IIQQ', e[:0x18])
        nlen = struct.unpack('<I', e[0x1C:0x20])[0]
        name = ft[i * 0x20 + 0x20:i * 0x20 + 0x20 + nlen].decode('utf-8')
        files.append((parent, off, size, name))
    dirs = []
    for i in range(len(dt) // 0x18):
        e = dt[i * 0x18:(i + 1) * 0x18]
        parent, sib, child, fchild = struct.unpack('<4I', e[:0x10])
        nlen = struct.unpack('<I', e[0x14:0x18])[0]
        name = dt[i * 0x18 + 0x18:i * 0x18 + 0x18 + nlen].decode('utf-8')
        dirs.append((parent, child, fchild, name))

    def dpath(i):
        if i == 0:
            return ''
        return dpath(dirs[i][0]) + '/' + dirs[i][3]

    out = []
    for parent, off, size, name in files:
        out.append((dpath(parent) + '/' + name, base + off, size))
    return out, base


def main():
    cmd, nca_p, tik = sys.argv[1], sys.argv[2], sys.argv[3]
    nca = Nca(nca_p, tik)
    print('[i] keygen=%d romfs_sec=0x%x..0x%x titlekey=%s'
          % (nca.keygen, nca.rom_base, nca.rom_end, nca.titlekey.hex()))
    if cmd == 'info':
        for i, (a, b) in enumerate(nca.secs):
            if b > a:
                print('  sec%d 0x%x..0x%x (%d)' % (i, a, b, b - a))
        return
    files, base = parse_romfs(nca)
    files.sort()
    if cmd == 'list':
        sub = ''
        for a in sys.argv[4:]:
            if a.startswith('--substr='):
                sub = a.split('=', 1)[1].upper()
        for p, off, size in files:
            if not sub or sub in p.upper():
                print('%-40s off=0x%09x size=%d' % (p, off, size))
        print('[i] total %d files' % len(files))
        return
    if cmd == 'get':
        want, dst = sys.argv[4], sys.argv[5]
        for p, off, size in files:
            if p == want:
                os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
                with open(dst, 'wb') as w:
                    pos = 0
                    while pos < size:
                        n = min(16 << 20, size - pos)
                        w.write(nca.read(off + pos, n))
                        pos += n
                print('[+] %s -> %s (%d B) head=%s' % (p, dst, size, open(dst, 'rb').read(8)))
                return
        print('[!] not found:', want)


if __name__ == '__main__':
    main()
