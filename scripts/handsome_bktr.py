#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ハンサムロンダリング 更新档（Patch RomFS / BKTR）比对工具。

复制自 scripts/bktr_romfs.py 的结构（原文件不动），针对本作修正两处：
  1) rel/sub 表本身按「普通段 CTR」读：iv = (hi << 64) | ((sec_start + off) // 16)，
     而不是 subsection 的 4+4 拆分（原工具用拆分式读 rel 表 ⇒ 桶计数读成天文数字）。
  2) 数据块按 subsection 的 ctr 读：iv = (hi << 64) | (ctr << 32) | ((sec_start + off) >> 4)。

校准（2026-10-26，1.3.0 v262144）：
  keygen=21 / Titlekey crypto ⇒ titlekey = AES-ECB-dec(titlekek_14, tik[0x180:0x190])
    = 59a798c516bf0b542a9e389580415f3f
  hi = LE-u64(fsh+0x140) = 0x0000000200000003（base 为 0x0000000200000000）
  自证：rel 表 pad==0 / bucket_count==1 / total 与 romfs 头一致

用法：
  python scripts/handsome_bktr.py <update.nsp|nca> --info
  python scripts/handsome_bktr.py <update.nsp> --list [--base <base.xci>]
  python scripts/handsome_bktr.py <update.nsp> --get <子串> --out <dir> [--base <base.xci>] [--ranges]
"""
import sys, os, struct

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import switch_nca as SN
from Crypto.Cipher import AES
from Crypto.Util import Counter


def pfs0(path):
    f = open(path, 'rb')
    h = f.read(0x10)
    if h[:4] != b'PFS0':
        f.close()
        return []
    n, strsz = struct.unpack_from('<II', h, 4)
    ents = []
    for i in range(n):
        off, size, so, _ = struct.unpack('<QQII', f.read(0x18))
        ents.append([off, size, so])
    st = f.read(strsz)
    f.close()
    data = 0x10 + n * 0x18 + strsz
    return [(st[e[2]:st.index(b'\0', e[2])].decode('utf-8', 'replace'), data + e[0], e[1]) for e in ents]


class Upd:
    def __init__(self, path, keyset='_sw/merged.keys'):
        self.path = path
        self.keys = SN.load_keys(keyset)
        self.f = open(path, 'rb')
        ents = pfs0(path)
        if ents:
            tik = next(x for x in ents if x[0].endswith('.tik'))
            self.f.seek(tik[1])
            self.tik = self.f.read(tik[2])
            nca = max((x for x in ents if x[0].endswith('.nca') and 'cnmt' not in x[0]), key=lambda x: x[2])
            self.nca_off, self.nca_size, self.nca_name = nca[1], nca[2], nca[0]
        else:
            self.tik = None
            self.nca_off, self.nca_size, self.nca_name = 0, os.path.getsize(path), os.path.basename(path)
        self.f.seek(self.nca_off)
        self.hdr = SN.xts_decrypt(bytes.fromhex(self.keys['header_key'][:32]),
                                  bytes.fromhex(self.keys['header_key'][32:64]), 0, self.f.read(0x4000))
        assert self.hdr[0x200:0x204] == b'NCA3'
        self.keygen = self.hdr[0x220]
        self.rights = self.hdr[0x230:0x240]
        self.key = self._key()
        self.secs = []
        for i in range(4):
            e = self.hdr[0x240 + i * 0x10:0x250 + i * 0x10]
            self.secs.append((int.from_bytes(e[0:4], 'little') * 0x200,
                              int.from_bytes(e[4:8], 'little') * 0x200))
        self.sid = next(i for i in range(4)
                        if self.hdr[0x400 + i * 0x200 + 8:0x400 + i * 0x200 + 12] == b'IVFC')
        self.sec_start, self.sec_end = self.secs[self.sid]
        fsh = self.hdr[0x400 + self.sid * 0x200:0x600 + self.sid * 0x200]
        self.fsh = fsh
        self.hi = int.from_bytes(fsh[0x140:0x148], 'little')
        self.rel = struct.unpack_from('<QQ', fsh, 0x100)
        self.sub = struct.unpack_from('<QQ', fsh, 0x120)
        self.relocs = self._read_relocs()
        self.subs = self._read_subs()
        self.total = self.relocs[-1][0] if self.relocs else 0

    def _key(self):
        if any(self.rights):
            blk = self.tik[0x180:0x190]
            rev = self.hdr[0x220]
            for r in (rev - 1, rev):
                k = self.keys.get('titlekek_%02x' % r)
                if k:
                    return AES.new(bytes.fromhex(k), AES.MODE_ECB).decrypt(blk)
            raise SystemExit('没有 titlekek')
        kaek = self.keys.get('key_area_key_application_%02x' % max(self.hdr[0x207], self.hdr[0x220] - 1))
        return AES.new(bytes.fromhex(kaek), AES.MODE_ECB).decrypt(self.hdr[0x300 + 2 * 16:0x300 + 3 * 16])

    def _plain(self, off, n):
        iv = (self.hi << 64) | ((self.sec_start + off) // 16)
        c = AES.new(self.key, AES.MODE_CTR, counter=Counter.new(128, initial_value=iv))
        self.f.seek(self.nca_off + self.sec_start + off)
        return c.decrypt(self.f.read(n))

    def _data(self, off, n, ctr):
        iv = (self.hi << 64) | (ctr << 32) | (((self.sec_start + off) >> 4) & 0xFFFFFFFF)
        c = AES.new(self.key, AES.MODE_CTR, counter=Counter.new(128, initial_value=iv))
        self.f.seek(self.nca_off + self.sec_start + off)
        return c.decrypt(self.f.read(n))

    def _read_relocs(self):
        b = self.rel[0]
        d = self._plain(b, self.rel[1] if self.rel[1] else 0x8000)
        pad, nb, tot = struct.unpack_from('<IIQ', d, 0)
        self.rel_header = (pad, nb, tot)
        out = []
        for k in range(nb):
            bo = k * 0x4000 + 0x4000 - 0x4000
            _, ne, _end = struct.unpack_from('<IIQ', d, 0x4000 + k * 0x4000)
            for j in range(ne):
                vo, po, ip = struct.unpack_from('<QQI', d, 0x4000 + k * 0x4000 + 0x10 + j * 0x14)
                out.append((vo, po, ip))
        out.sort()
        return out

    def _read_subs(self):
        b = self.sub[0]
        d = self._plain(b, self.sub[1] if self.sub[1] else 0x8000)
        _, nb, tot = struct.unpack_from('<IIQ', d, 0)
        self.sub_header = (nb, tot)
        out = []
        for k in range(nb):
            _, ne, _end = struct.unpack_from('<IIQ', d, 0x4000 + k * 0x4000)
            for j in range(ne):
                off, _8, ctr = struct.unpack_from('<QII', d, 0x4000 + k * 0x4000 + 0x10 + j * 0x10)
                out.append((off, ctr))
        out.sort()
        return out

    def _ctr_at(self, rel):
        cur = 0
        for off, ctr in self.subs:
            if off <= rel:
                cur = ctr
            else:
                break
        return cur

    def vread_patch(self, v, n):
        """只读 patch 区间；返回 (bytes, ok)"""
        out = bytearray()
        while n > 0:
            cur = None
            nxt = None
            for e in self.relocs:
                if e[0] <= v:
                    cur = e
                else:
                    nxt = e[0]
                    break
            if cur is None:
                return bytes(out), False
            if not cur[2]:
                return bytes(out), False
            k = min(n, (nxt - v) if nxt else n)
            off = cur[1] + (v - cur[0])
            out += self._data(off, k, self._ctr_at(off))
            v += k
            n -= k
        return bytes(out), True

    def changed_ranges(self):
        out = []
        for i, (vo, po, ip) in enumerate(self.relocs):
            if not ip:
                continue
            end = self.relocs[i + 1][0] if i + 1 < len(self.relocs) else self.rel_header[2]
            out.append((vo, end, po))
        return out


class Base:
    """base XCI 的 romfs 虚拟读（复用 scripts/handsome_nca.py 的桶树实现）。"""

    def __init__(self, path, base_off, key_hex, keyset='_sw/merged.keys'):
        os.environ['NCA_KEY'] = key_hex
        import importlib
        import handsome_nca as W
        self.sec = W.Sec(path, base=base_off, keyset=keyset)
        self.b = W.BucketRomfs(self.sec, 1)
        self.b.sid = 1

    def read(self, off, n):
        return self.b.read(off, n)


def parse_romfs(v):
    (hs, dh_ofs, dh_sz, dm_ofs, dm_sz, fh_ofs, fh_sz, fm_ofs, fm_sz, fd_ofs) = struct.unpack('<10Q', v.read(0, 0x50))
    dm = v.read(dm_ofs, dm_sz)
    fm = v.read(fm_ofs, fm_sz)

    def dir_info(off):
        par, nxt, cd, cf, h, nl = struct.unpack_from('<IIIIII', dm, off)
        return nxt, cd, cf, dm[off + 0x18:off + 0x18 + nl].decode('utf-8', 'replace')

    def file_info(off):
        par, nxt, dofs, dsz, h, nl = struct.unpack_from('<IIQQII', fm, off)
        return nxt, dofs, dsz, fm[off + 0x20:off + 0x20 + nl].decode('utf-8', 'replace')

    files = []

    def walk(doff, prefix):
        _, cd, cf, _ = dir_info(doff)
        o = cf
        while o != 0xFFFFFFFF and o < len(fm):
            nxt, dofs, dsz, nm = file_info(o)
            files.append((prefix + nm, fd_ofs + dofs, dsz))
            if nxt == o:
                break
            o = nxt
        o = cd
        while o != 0xFFFFFFFF and o < len(dm):
            nxt, _, _, nm = dir_info(o)
            walk(o, prefix + nm + '/')
            if nxt == o:
                break
            o = nxt

    walk(0, '')
    return files, fd_ofs


class Virt:
    def __init__(self, upd, base=None):
        self.upd, self.base = upd, base

    def read(self, off, n):
        out = bytearray()
        while n > 0:
            d, ok = self.upd.vread_patch(off, n)
            out += d
            off += len(d)
            n -= len(d)
            if n <= 0:
                break
            if not ok:
                if self.base is None:
                    raise SystemExit('虚拟 %#x 落在 base 区间，需要 --base' % off)
                # 连续 base 区间
                m = min(n, 1 << 20)
                out += self.base.read(off, m)
                off += m
                n -= m
        return bytes(out)

    def romfs_start(self):
        # romfs 头 header_size==0x50：由 rel 区间起点试探（本作 virt 0 即 romfs 头）
        for v in (0, 0x4000, 0x200):
            try:
                if struct.unpack('<Q', self.read(v, 8))[0] == 0x50:
                    return v
            except SystemExit:
                continue
        raise SystemExit('定不到 romfs 头')


def main():
    path = sys.argv[1]
    args = sys.argv[2:]
    u = Upd(path)
    print('[i] NCA %s %d B keygen=%d rights=%s' % (u.nca_name, u.nca_size, u.keygen, u.rights.hex()))
    print('[i] section%d %#x..%#x  hi=%#x' % (u.sid, u.sec_start, u.sec_end, u.hi))
    print('[i] rel pad=%d buckets=%d total=%#x  subs=%d  entries=%d' %
          (u.rel_header[0], u.rel_header[1], u.rel_header[2], len(u.subs), len(u.relocs)))
    ch = u.changed_ranges()
    print('[i] changed ranges=%d  bytes=%d' % (len(ch), sum(b - a for a, b, _ in ch)))
    if '--ranges' in args:
        for a, b, p in ch[:20]:
            print('    %#010x..%#010x  %d' % (a, b, b - a))
    base = None
    if '--base' in args:
        bp = args[args.index('--base') + 1]
        base = Base(bp, 0x1F033, '764ea2ad02a123cd860822303341bbb3')
    if '--info' in args:
        return
    v = Virt(u, base)
    rs = v.romfs_start()
    print('[i] romfs @%#x' % rs)
    files, fd = parse_romfs_off(v, rs)
    print('[i] update files=%d' % len(files))
    for n, o, s in files:
        if 'sharedassets1.assets' in n or n.endswith('resources.assets'):
            print('    %-60s off=%#x size=%d' % (n, o, s))
    if '--list' in args:
        for n, o, s in files:
            print('%12d %s' % (s, n))
        return
    if '--get' in args:
        sub = args[args.index('--get') + 1]
        out = args[args.index('--out') + 1]
        for n, o, s in files:
            if sub.lower() in n.lower():
                p = os.path.join(out, n)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, 'wb') as w:
                    for k in range(0, s, 1 << 22):
                        w.write(v.read(o + k, min(1 << 22, s - k)))
                print('   -> %s (%d)' % (p, s))


class OffReader:
    def __init__(self, v, base):
        self.v, self.base = v, base

    def read(self, off, n):
        return self.v.read(self.base + off, n)


def parse_romfs_off(v, rs):
    return parse_romfs(OffReader(v, rs))


if __name__ == '__main__':
    main()
