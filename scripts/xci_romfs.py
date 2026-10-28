#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""XCI -> (内存中)NCA -> RomFS 单文件抽取（不落 NCA/整 romfs，省磁盘）。

背景：nsz 重打包出来的 XCI 过不了 hactool 的 hfs0_header_hash（`XCI partition is corrupt!`），
而 `hactool -t xci --securedir` 会把整套 NCA 再拷一份（7 GB 级）。磁盘紧张时改用本工具：
直接按 HFS0 表定位 NCA 在 XCI 里的偏移，用 `switch_nca` 的 XTS/CTR 解密就地解析 romfs，
只把需要的那几个文件落盘。

用法:
  python scripts/xci_romfs.py <x.xci> --list
  python scripts/xci_romfs.py <x.xci> --get CONTENTS/STORY.cpk --out _w_X/story.cpk
  python scripts/xci_romfs.py <x.xci> --getall --out-dir _w_X/romfs   # 注意磁盘
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import switch_nca as S
from Crypto.Cipher import AES
from Crypto.Util import Counter

KEYSET = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '_sw', 'prod_fixed.keys')


def hfs0_partitions(path, scan=64 << 20):
    """扫描前 64MB，返回 [(off, {name: (off, size)})]。"""
    with open(path, 'rb') as f:
        buf = f.read(scan)
    out = []
    i = buf.find(b'HFS0')
    while i >= 0:
        try:
            num, strsz = struct.unpack_from('<II', buf, i + 4)
            if not (0 < num < 4096 and 0 < strsz < (1 << 20)):
                raise ValueError
            ent = i + 0x10
            names = buf[ent + num * 0x40: ent + num * 0x40 + strsz]
            data = ent + num * 0x40 + strsz
            d = {}
            for k in range(num):
                off, size, no, _h = struct.unpack_from('<QQII', buf, ent + k * 0x40)
                name = names[no:names.find(b'\0', no)].decode('utf-8', 'replace')
                d[name] = (data + off, size)
            out.append((i, d))
        except Exception:
            pass
        i = buf.find(b'HFS0', i + 4)
    return out


class Sub:
    """XCI 内某段的只读视图。"""

    def __init__(self, path, base, size):
        self.f = open(path, 'rb')
        self.base, self.size, self.pos = base, size, 0

    def read(self, n=-1):
        if n < 0:
            n = self.size - self.pos
        n = min(n, self.size - self.pos)
        if n <= 0:
            return b''
        self.f.seek(self.base + self.pos)
        d = self.f.read(n)
        self.pos += len(d)
        return d

    def seek(self, p, w=0):
        self.pos = p
        return p

    def tell(self):
        return self.pos


class Nca:
    """Standard crypto（Gamecard）Program NCA。"""

    def __init__(self, path, off, size, keys):
        self.f = Sub(path, off, size)
        self.keys = keys
        self.hdr = S.xts_decrypt(bytes.fromhex(keys['header_key'][:32]),
                                bytes.fromhex(keys['header_key'][32:64]), 0, self.f.read(0x1600))
        assert self.hdr[0x200:0x204] == b'NCA3', 'bad NCA3'
        self.secs = []
        for i in range(4):
            e = self.hdr[0x240 + i * 0x10:0x250 + i * 0x10]
            self.secs.append((int.from_bytes(e[0:4], 'little') * 0x200,
                              int.from_bytes(e[4:8], 'little') * 0x200))
        keygen = self.hdr[0x206]
        # 内容密钥：以 romfs 头（u64 header_size==0x50）为已知明文锚定，在
        # key_area_key_application_XX × key_area 槽 里定一组（本作 = _11 / 槽2）。
        self.key = self._pick_key(keys)
        self.keygen = keygen
        # section1 = RomFS（IVFC）
        base = 0x400 + 1 * 0x200
        assert self.hdr[base + 0x08:base + 0x0c] in (b'IVFC', b'FATC'), self.hdr[base + 0x08:base + 0x0c]
        # section_ctr(u64 LE @0x140) 作 counter 高 8B（大端），故字节起点 +0x141
        self.ctr_hi = self.hdr[base + 0x141:base + 0x149]
        self.sec_off = self.secs[1][0]
        lv = [struct.unpack_from('<QQII', self.hdr, base + 0x18 + 0x18 * i) for i in range(6)]
        self.lv5 = lv[5][0]
        self.romfs = self.sec_off + self.lv5

    def _dec(self, key, base, ln, slot_off=0):
        """按 (key, romfs 起点) 解 base 起 ln 字节；CTR 低位 = NCA 内绝对偏移/16。"""
        a = base
        ctr = self.ctr_hi + (a // 16).to_bytes(8, 'big')
        pad = a % 16
        self.f.seek(a - pad)
        raw = self.f.read(ln + pad)
        c = AES.new(key, AES.MODE_CTR,
                    counter=Counter.new(128, initial_value=int.from_bytes(ctr, 'big')))
        return c.decrypt(raw)[pad:pad + ln]

    def _pick_key(self, keys):
        base = 0x400 + 0x200
        lv = [struct.unpack_from('<QQII', self.hdr, base + 0x18 + 0x18 * i) for i in range(6)]
        cand = self.secs[1][0] + lv[5][0]
        best = None
        for kn in sorted(k for k in keys if k.startswith('key_area_key_application_')):
            kaek = bytes.fromhex(keys[kn])
            for slot in range(4):
                key = AES.new(kaek, AES.MODE_ECB).decrypt(self.hdr[0x300 + slot * 16:0x310 + slot * 16])
                self.ctr_hi = self.hdr[base + 0x141:base + 0x149]
                try:
                    d = self._dec(key, cand, 0x50)
                except Exception:
                    continue
                v = struct.unpack('<10Q', d)
                if v[0] == 0x50 and v[2] < 0x1000:
                    print('[i] key anchor: %s slot=%d' % (kn, slot))
                    return key
        raise SystemExit('romfs key anchor not found')

    def read(self, off, ln):
        return self._dec(self.key, self.romfs + off, ln)

    def files(self):
        v = struct.unpack('<10Q', self.read(0, 0x50))
        dm, fm = self.read(v[3], v[4]), self.read(v[7], v[8])

        def al(x):
            return (x + 3) & ~3

        dirs, out = [], []
        off = 0
        while off + 0x18 <= len(dm):
            parent, sib, child, fno, h, nl = struct.unpack_from('<IIIIII', dm, off)
            dirs.append([parent, dm[off + 0x18:off + 0x18 + nl].decode('utf-8', 'replace')])
            off += 0x18 + al(nl)

        def dpath(i):
            parts, seen = [], set()
            while i < len(dirs) and i not in seen:
                seen.add(i)
                parts.append(dirs[i][1])
                if dirs[i][0] == i:
                    break
                i = dirs[i][0]
            return '/'.join(reversed(parts))

        off = 0
        while off + 0x20 <= len(fm):
            parent, sib, dof, dsz, h, nl = struct.unpack_from('<IIQQII', fm, off)
            nm = fm[off + 0x20:off + 0x20 + nl].decode('utf-8', 'replace')
            base = dpath(parent) if parent < len(dirs) else ''
            out.append(((base + '/' if base else '/') + nm, dof, dsz))
            off += 0x20 + al(nl)
        return out

    def read_file(self, off, size, out=None, chunk=1 << 22):
        pos = 0
        if out:
            os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
            fh = open(out, 'wb')
        else:
            fh = None
            buf = bytearray()
        while pos < size:
            d = self.read(off + pos, min(chunk, size - pos))
            if not d:
                break
            if fh:
                fh.write(d)
            else:
                buf += d
            pos += len(d)
        if fh:
            fh.close()
            return pos
        return bytes(buf)


def open_xci(path):
    keys = S.load_keys(KEYSET)
    parts = hfs0_partitions(path)
    best = None
    for off, d in parts:
        if any(n.endswith('.nca') for n in d):
            tot = sum(s for _o, s in d.values())
            if best is None or tot > best[2]:
                best = (off, d, tot)
    if not best:
        raise SystemExit('no NCA-bearing HFS0 found')
    off, d, _tot = best
    return keys, d


def main():
    path = sys.argv[1]
    keys, ents = open_xci(path)
    ncas = []
    for name, (off, size) in ents.items():
        if not name.endswith('.nca'):
            continue
        try:
            n = Nca(path, off, size, keys)
        except Exception as e:
            print('[skip] %s %r' % (name, e))
            continue
        ncas.append((size, name, n))
        print('[nca] %-40s off=0x%-12x size=0x%-12x romfs_off=0x%x' % (name, off, size, n.romfs))
    if not ncas:
        raise SystemExit('no usable NCA')
    ncas.sort(reverse=True)
    n = ncas[0][2]
    print('[i] use %s (keygen %d)' % (ncas[0][1], n.keygen))
    files = n.files()
    if '--list' in sys.argv or len(sys.argv) == 2:
        for p, o, s in sorted(files):
            print('  %-50s %12d' % (p, s))
        print('[i] %d files, romfs=%d bytes' % (len(files), sum(s for _p, _o, s in files)))
        return
    if '--get' in sys.argv:
        want = sys.argv[sys.argv.index('--get') + 1]
        out = sys.argv[sys.argv.index('--out') + 1]
        for p, o, s in files:
            if p.lstrip('/') == want.lstrip('/') or p == want:
                w = n.read_file(o, s, out)
                print('[+] %s -> %s (%d bytes)' % (p, out, w))
                return
        raise SystemExit('not found: ' + want)
    if '--getall' in sys.argv:
        outdir = sys.argv[sys.argv.index('--out-dir') + 1]
        for p, o, s in files:
            dst = os.path.join(outdir, p.lstrip('/'))
            n.read_file(o, s, dst)
            print('[+] %s (%d)' % (p, s))
        return


if __name__ == '__main__':
    main()
