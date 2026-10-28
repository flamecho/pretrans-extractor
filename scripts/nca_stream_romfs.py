#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Switch 容器流式取 romfs 文件（不落 NCA/NSP 副本，省盘）。

支持 PFS0(NSP) / XCI(HEAD) → 直接按 (offset,size) 读内部 NCA；段解密自动在 4 种 CTR 方案里
用「结构自证」选定（压缩表 sanity / IVFC 魔数），压缩段走 LZ4 桶树。

用法:
  python scripts/nca_stream_romfs.py <容器> --list
  python scripts/nca_stream_romfs.py <容器> --files [--nca=<子串>]
  python scripts/nca_stream_romfs.py <容器> --get <子串> --out <dir> [--nca=<子串>]
"""
import os, sys, struct, glob
from Crypto.Cipher import AES
from Crypto.Util import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import switch_nca as SN


class Src:
    def __init__(self, path, base=0):
        self.f = open(path, 'rb')
        self.base = base

    def read_at(self, off, n):
        self.f.seek(self.base + off)
        return self.f.read(n)


def parse_pfs0(src):
    h = src.read_at(0, 0x10)
    assert h[:4] == b'PFS0', 'not PFS0'
    n, strsz = struct.unpack_from('<II', h, 4)
    ents = []
    for i in range(n):
        off, size, so, _ = struct.unpack('<QQII', src.read_at(0x10 + i * 0x18, 0x18))
        ents.append([off, size, so, ''])
    names = src.read_at(0x10 + n * 0x18, strsz).split(b'\0')
    data = 0x10 + n * 0x18 + strsz
    return [(nm.decode('utf-8', 'replace'), data + e[0], e[1]) for e, nm in zip(ents, names)]


def parse_xci(path):
    src = Src(path)
    root_off = struct.unpack_from('<Q', src.read_at(0x130, 8), 0)[0]
    h = src.read_at(root_off, 0x10)
    assert h[:4] == b'HFS0', 'root HFS0 magic'
    n, strsz = struct.unpack_from('<II', h, 4)
    ents = []
    for i in range(n):
        off, size, so, _ = struct.unpack('<QQII', src.read_at(root_off + 0x10 + i * 0x40, 0x18))
        ents.append((off, size))
    names = src.read_at(root_off + 0x10 + n * 0x40, strsz).split(b'\0')
    data = root_off + 0x10 + n * 0x40 + strsz
    parts = {nm.decode('utf-8', 'replace'): (data + off, size) for (off, size), nm in zip(ents, names)}
    sec = parts.get('secure')
    if not sec:
        return []
    base, size = sec
    h = src.read_at(base, 0x10)
    n, strsz = struct.unpack_from('<II', h, 4)
    out = []
    for i in range(n):
        off, sz, so, _ = struct.unpack('<QQII', src.read_at(base + 0x10 + i * 0x40, 0x18))
        out.append([off, sz, so, ''])
    names = src.read_at(base + 0x10 + n * 0x40, strsz).split(b'\0')
    data = base + 0x10 + n * 0x40 + strsz
    return [(nm.decode('utf-8', 'replace'), data + o, s) for (o, s, _, _), nm in zip(out, names)]


def find_tik(path, rights):
    d = os.path.dirname(os.path.abspath(path))
    for tik in glob.glob(os.path.join(d, '*.tik')):
        try:
            t = open(tik, 'rb').read(0x300)
        except OSError:
            continue
        if t[0x2A0:0x2B0] == rights:
            return tik
    return None


class Nca:
    def __init__(self, path, off, keys, tik_bytes=None):
        self.src = Src(path, off)
        self.keys = keys
        hdr = SN.xts_decrypt(bytes.fromhex(keys['header_key'][:32]),
                             bytes.fromhex(keys['header_key'][32:64]), 0, self.src.read_at(0, 0x4000))
        assert hdr[0x200:0x204] == b'NCA3', 'NCA magic != NCA3'
        self.hdr = hdr
        self.keygen = max(hdr[0x206], hdr[0x220])
        self.rights = hdr[0x230:0x240]
        self.secs = []
        for i in range(4):
            e = hdr[0x240 + i * 0x10:0x250 + i * 0x10]
            self.secs.append((int.from_bytes(e[0:4], 'little') * 0x200,
                              int.from_bytes(e[4:8], 'little') * 0x200))
        self.key = None
        if any(self.rights):
            t = tik_bytes if (tik_bytes and tik_bytes[0x2A0:0x2B0] == self.rights) else None
            if t is None:
                p = find_tik(path, self.rights)
                if p:
                    t = open(p, 'rb').read(0x300)
            if t:
                kek = bytes.fromhex(keys['titlekek_%02x' % (self.keygen - 1)])
                self.key = AES.new(kek, AES.MODE_ECB).decrypt(t[0x180:0x190])
        if self.key is None:
            kaek = bytes.fromhex(keys['key_area_key_application_%02x' % (self.keygen - 1)])
            self.key = AES.new(kaek, AES.MODE_ECB).decrypt(hdr[0x300 + 2 * 16:0x300 + 3 * 16])
        self.levels = {}
        self.scheme = {}
        for sid in range(4):
            b = 0x400 + sid * 0x200
            lv = [struct.unpack_from('<QQI', hdr, b + 0x18 + i * 0x18) for i in range(6)]
            self.levels[sid] = (hdr[b + 8:b + 12], lv, struct.unpack_from('<QQ', hdr, b + 0x178))
            self.scheme[sid] = self._detect(sid) if lv[5][1] else None

    def _dec(self, sid, off, n, mode):
        st = self.secs[sid][0]
        ctr8 = self.hdr[0x400 + sid * 0x200 + 0x140:0x400 + sid * 0x200 + 0x148]
        if mode == 'p02':
            init = (2 << 96) | ((st + off) // 16)
        elif mode == 'hdr':
            init = (int.from_bytes(ctr8, 'big') << 64) | ((st + off) // 16)
        elif mode == 'hdr_rel':
            init = (int.from_bytes(ctr8, 'big') << 64) | (off // 16)
        else:
            init = (st + off) // 16
        d = self.src.read_at(st + off, n)
        return AES.new(self.key, AES.MODE_CTR,
                       counter=Counter.new(128, initial_value=init & ((1 << 128) - 1))).decrypt(d)

    def _detect(self, sid):
        _, lv, comp = self.levels[sid]
        doff, dsize = lv[5][0], lv[5][1]
        for mode in ('hdr', 'p02', 'hdr_rel', 'zero'):
            if comp[0] or comp[1]:
                h = self._dec(sid, doff + comp[0], 0x10, mode)
                nb = struct.unpack_from('<I', h, 4)[0]
                tot = struct.unpack_from('<Q', h, 8)[0]
                if 0 < nb < 4096 and abs(tot - dsize) < 0x100000:
                    return mode
            else:
                if self._dec(sid, 0, 0x10, mode)[:4] == b'IVFC':
                    return mode
        return None

    def read(self, sid, off, n):
        return self._dec(sid, off, n, self.scheme[sid])


class SecRomfs:
    def __init__(self, nca, sid):
        self.n, self.sid = nca, sid
        magic, lv, comp = nca.levels[sid]
        self.doff, self.dsize = lv[5][0], lv[5][1]
        self.total = self.dsize
        self.ents = None
        self.cache = {}
        if comp[0] or comp[1]:
            tbl = self.doff + comp[0]
            h = nca.read(sid, tbl, 0x10)
            nb = struct.unpack_from('<I', h, 4)[0]
            tot = struct.unpack_from('<Q', h, 8)[0]
            ents = []
            for b in range(nb):
                bh = nca.read(sid, tbl + 0x4000 + b * 0x4000, 0x10)
                cnt = struct.unpack_from('<I', bh, 4)[0]
                raw = nca.read(sid, tbl + 0x4000 + b * 0x4000 + 0x10, cnt * 0x18)
                for k in range(cnt):
                    ents.append(struct.unpack_from('<QQII', raw, k * 0x18))
            self.ents = sorted(ents)
            self.total = tot

    def block(self, i):
        if i in self.cache:
            return self.cache[i]
        v, p, typ, sz = self.ents[i]
        end = self.ents[i + 1][0] if i + 1 < len(self.ents) else self.total
        n = end - v
        if typ == 0:
            data = self.n.read(self.sid, self.doff + p, n)
        else:
            import lz4.block
            data = lz4.block.decompress(self.n.read(self.sid, self.doff + p, sz), uncompressed_size=n)
        if len(self.cache) > 256:
            self.cache.clear()
        self.cache[i] = data
        return data

    def read(self, off, ln):
        if self.ents is None:
            return self.n.read(self.sid, self.doff + off, ln)
        out = bytearray()
        while ln > 0:
            i = self._loc(off)
            v = self.ents[i][0]
            b = self.block(i)
            s = off - v
            take = min(len(b) - s, ln)
            if take <= 0:
                raise RuntimeError('bad block at %d' % off)
            out += b[s:s + take]
            off += take
            ln -= take
        return bytes(out)

    def _loc(self, off):
        lo, hi = 0, len(self.ents)
        while lo + 1 < hi:
            mid = (lo + hi) // 2
            if self.ents[mid][0] <= off:
                lo = mid
            else:
                hi = mid
        return lo


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


def main():
    path = sys.argv[1]
    args = sys.argv[2:]
    keys = SN.load_keys('_sw/prod_fixed.keys')
    with open(path, 'rb') as f:
        magic = f.read(4)
    ncas = parse_pfs0(Src(path)) if magic == b'PFS0' else parse_xci(path)
    for a in args:
        if a.startswith('--nca='):
            sub = a.split('=', 1)[1].lower()
            ncas = [n for n in ncas if sub in n[0].lower()]
    ncas.sort(key=lambda t: -t[2])
    if '--list' in args:
        for nm, off, sz in ncas:
            print('%12d  @0x%x  %s' % (sz, off, nm))
        return
    if not ncas:
        print('no NCA'); return
    nm, off, sz = ncas[0]
    tik_bytes = None
    if magic == b'PFS0':
        for n2, o2, s2 in parse_pfs0(Src(path)):
            if n2.lower().endswith('.tik'):
                tik_bytes = Src(path).read_at(o2, s2)
                print('[i] tik %s %d B' % (n2, s2))
    print('[i] NCA %s size=%d' % (nm, sz))
    nca = Nca(path, off, keys, tik_bytes)
    print('[i] keygen=%d rights=%s key=%s scheme=%s' % (nca.keygen, nca.rights.hex(), nca.key.hex(), nca.scheme))
    sid = next((s for s in range(4) if nca.levels[s][0] == b'IVFC'), None)
    if sid is None:
        for s in range(4):
            print('   sec%d magic=%r size=%d' % (s, nca.levels[s][0], nca.levels[s][1][5][1]))
        return
    print('[i] romfs section %d comp=%s' % (sid, nca.levels[sid][2]))
    v = SecRomfs(nca, sid)
    files, fd = parse_romfs(v)
    print('[i] files=%d data_base=0x%x' % (len(files), fd))
    if '--files' in args:
        for n, o, s in files:
            print('%10d  %s' % (s, n))
    get = out = None
    for i, a in enumerate(args):
        if a == '--get':
            get = args[i + 1]
        if a == '--out':
            out = args[i + 1]
    if get and out:
        for n, o, s in files:
            if get.lower() in n.lower():
                p = os.path.join(out, n.replace('/', os.sep))
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, 'wb') as w:
                    for k in range(0, s, 0x400000):
                        w.write(v.read(o + k, min(0x400000, s - k)))
                print('   -> %s (%d)' % (n, s))


if __name__ == '__main__':
    main()
