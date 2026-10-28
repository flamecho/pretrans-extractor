#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""官方更新档（BKTR Patch RomFS）→ 本体 romfs 合并读取（hactool 对这类重打包件报
`BKTR section seems to be corrupted`，bktr_romfs.py 又会把表区读串，故自建最小实现）。

要点（2026-10-26 新テニス v1.0.3 实测）：
  · 虚拟偏移 = **更新段内偏移**，romfs 起点 = IVFC level5 的 logical_offset（与本体同值）。
  · 段内容一律 **普通段 CTR**（hi<<64 | (段内绝对偏移>>4)），不用 subsection 的 4+4 拆分式。
  · relocation 表的区间必须用**桶头 virt_end** 收尾（不能拿下一个 entry 的 vo 兜，
    否则会造出 60MB 假区间，整个文件表都对不上）。
  · base 区间：entry.po 与虚拟同值（段内偏移）⇒ 本体镜像偏移 = po − romfs_v。

用法：
  python scripts/bktr_merge.py --update upd.nsp --base-romfs base.romfs [--list]
        [--get 路径子串 --outdir DIR]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bktr_romfs as B
from Crypto.Cipher import AES
from Crypto.Util import Counter

NULL = object()   # 「用普通段 CTR」的哨兵


class Sec:
    """更新段读：普通 CTR。

    ★ 段密钥不一定按「段号 == key_area 块号」取（实测 もし神様 本体 sec1 的密钥在 blk2）。
    给出 romfs_hint 时用「该处 8 字节是否 == 0x50」自证，逐个候选试。
    """

    def __init__(self, nca, idx, romfs_hint=None):
        self.nca, self.idx = nca, idx
        st, en = nca.secs[idx]
        self.start, self.size = st, en - st
        self.hi = nca.sec_hi(idx)
        self.key = self._pick(romfs_hint)
        if self.key is None:
            raise SystemExit('段 %d 无内容密钥' % idx)

    def _cands(self):
        n = self.nca
        out = []
        if n.keys_by_sec.get(self.idx):
            out.append(n.keys_by_sec[self.idx])
        for k in n.alt_keys:
            if k not in out:
                out.append(k)
        if n.rights == b'\0' * 16:
            for i in range(0, 0x20):
                kak = n.keys.get('key_area_key_application_%02x' % i)
                if not kak:
                    continue
                for b in range(4):
                    blk = n.key_area[b * 16:b * 16 + 16]
                    if blk == bytes(16):
                        continue
                    k = AES.new(bytes.fromhex(kak), AES.MODE_ECB).decrypt(blk)
                    if k not in out:
                        out.append(k)
        return out

    def _pick(self, hint):
        if hint is None:
            return self._cands()[0] if self._cands() else None
        for k in self._cands():
            for iv in self._ivs(hint):
                try:
                    self.nca.f.seek(self.start + hint)
                    body = self.nca.f.read(16)
                    d = AES.new(k, AES.MODE_CTR,
                                counter=Counter.new(128, initial_value=int.from_bytes(iv, 'big'))).decrypt(body)
                    if d[0] == 0x50 and d[1:8] == bytes(7):
                        self.table_ctr = iv[4:8]
                        return k
                except Exception:
                    continue
        return None

    def _ivs(self, rel):
        a = self.start + rel
        low = ((a & ~0xF) >> 4).to_bytes(8, 'big')
        out = [self.hi + low]                       # 普通段 CTR
        for ctr in range(4):                        # subsection：hi 的低 4 字节换成 ctr
            out.append(self.hi[:4] + ctr.to_bytes(4, 'big') + low)
        return out

    def read(self, rel, n, ctr=NULL):
        if rel >= self.size:
            raise SystemExit('段内偏移 %#x 越界（段长 %#x）' % (rel, self.size))
        n = min(n, self.size - rel)
        a = self.start + rel
        self.nca.f.seek(a)
        body = self.nca.f.read((n + 15) // 16 * 16)
        if ctr is NULL:
            iv = self.hi + ((a & ~0xF) >> 4).to_bytes(8, 'big')
        else:
            iv = self.hi[:4] + int(ctr).to_bytes(4, 'big') + ((a & ~0xF) >> 4).to_bytes(8, 'big')
        p = AES.new(self.key, AES.MODE_CTR,
                    counter=Counter.new(128, initial_value=int.from_bytes(iv, 'big'))).decrypt(body)
        return p[:n]


class Bktr2:
    def __init__(self, nca, idx, img, romfs_hint=None):
        self.nca, self.idx, self.img = nca, idx, img
        fsh = nca.fsh[idx]
        self.levels = [struct.unpack_from('<QQQ', fsh, 0x18 + i * 0x18)
                       for i in range(struct.unpack_from('<I', fsh, 0x14)[0])]
        lv5 = self.levels[5][0] if len(self.levels) > 5 else None
        self.sec = Sec(nca, idx, romfs_hint if romfs_hint is not None else lv5)
        self.romfs = None
        self.entries = self._relocs(fsh)
        self.subs = self._subs(fsh)
        self._idx = [e[0] for e in self.entries]
        for lo, sz, _ in self.levels:
            if not sz:
                continue
            try:
                if struct.unpack('<Q', self.read_v(lo, 8))[0] == 0x50:
                    self.romfs = lo
                    break
            except (SystemExit, Exception):
                continue
        if self.romfs is None:
            if romfs_hint is not None:
                self.romfs = romfs_hint
            else:
                raise SystemExit('定位不到虚拟 romfs 头')

    # -- 表解析（普通 CTR）
    def _relocs(self, fsh):
        off, sz, mg, ver, num, _ = struct.unpack_from('<QQIIII', fsh, 0x100)
        hdr = self.sec.read(off, 0x10)
        nb = struct.unpack_from('<I', hdr, 4)[0]
        out = []
        for k in range(nb):
            bo = off + 0x4000 + k * 0x4000
            h = self.sec.read(bo, 0x10)
            ne = struct.unpack_from('<I', h, 4)[0]
            vend = struct.unpack_from('<Q', h, 8)[0]
            raw = self.sec.read(bo + 0x10, ne * 0x14)
            ent = [struct.unpack_from('<QQI', raw, j * 0x14) for j in range(ne)]
            for j, (vo, po, ip) in enumerate(ent):
                end = ent[j + 1][0] if j + 1 < ne else vend
                out.append((vo, po, ip, end))
        out.sort()
        return out

    def _subs(self, fsh):
        off, sz, mg, ver, num, _ = struct.unpack_from('<QQIIII', fsh, 0x120)
        nb = struct.unpack_from('<I', self.sec.read(off, 0x10), 4)[0]
        out = []
        for k in range(nb):
            bo = off + 0x4000 + k * 0x4000
            h = self.sec.read(bo, 0x10)
            ne = struct.unpack_from('<I', h, 4)[0]
            vend = struct.unpack_from('<Q', h, 8)[0]
            raw = self.sec.read(bo + 0x10, ne * 0x10)
            ent = [struct.unpack_from('<QII', raw, j * 0x10) for j in range(ne)]
            for j, (o, u, ctr) in enumerate(ent):
                end = ent[j + 1][0] if j + 1 < ne else vend
                out.append((o, ctr, end))
        out.sort()
        return out

    def map_of(self, v):
        import bisect
        i = bisect.bisect_right(self._idx, v) - 1
        if i < 0:
            return None
        vo, po, ip, end = self.entries[i]
        if v >= end:
            return None
        return po + (v - vo), ip

    def ctr_at(self, po):
        """subsection 表：物理偏移 → CTR 值（hi 的低 4 字节）。"""
        cur, end = 0, None
        for o, ctr, e in self.subs:
            if o <= po:
                cur, end = ctr, e
            else:
                break
        return cur, (end if end is not None else po + 0x4000)

    def read_v(self, v, n):
        out = bytearray()
        while n > 0:
            m = self.map_of(v)
            if m is None:
                raise SystemExit('虚拟偏移 %#x 无映射' % v)
            po, ip = m
            import bisect
            i = bisect.bisect_right(self._idx, v) - 1
            k = min(n, self.entries[i][3] - v)
            if ip:
                ctr, send = self.ctr_at(po)
                k = max(1, min(k, send - po))
                out += self.sec.read(po, k, ctr)
            else:
                # base 区间：虚拟偏移与本体 romfs 偏移只差 romfs 起点（entry.po 有 ±0x70 级偏移，不可用）
                out += self.img.read(v - self.romfs, k)
            v += k
            n -= k
        return bytes(out)

    def patch_ranges(self):
        return [(vo, end) for vo, po, ip, end in self.entries if ip]


class Image:
    def __init__(self, path):
        self.f = open(path, 'rb')
        self.size = os.path.getsize(path)

    def read(self, off, n):
        if off < 0 or off >= self.size:
            raise SystemExit('本体镜像偏移 %#x 越界' % off)
        self.f.seek(off)
        return self.f.read(min(n, self.size - off))


def parse_tables(rv, read):
    h = struct.unpack('<10Q', read(rv, 0x50))
    (hdr_size, dh_off, dh_sz, dm_off, dm_sz,
     fh_off, fh_sz, fm_off, fm_sz, data_off) = h
    if hdr_size != 0x50:
        raise SystemExit('romfs 头无效')
    dm = read(rv + dm_off, dm_sz)
    fm = read(rv + fm_off, fm_sz)
    dirs, p = {}, 0
    while p + 0x18 <= len(dm):
        par, sib, ch, fi, hsh, nl = struct.unpack_from('<IIIIII', dm, p)
        dirs[p] = (par, dm[p + 0x18:p + 0x18 + nl].decode('utf-8', 'replace'))
        p += (0x18 + nl + 3) & ~3
    cache = {}

    def dpath(o):
        if o in cache:
            return cache[o]
        d = dirs.get(o)
        if d is None or o == 0:
            cache[o] = ''
            return ''
        up = dpath(d[0])
        cache[o] = (up + '/' + d[1]) if up else d[1]
        return cache[o]

    files, p = [], 0
    while p + 0x20 <= len(fm):
        par, sib, fo, sz, hsh, nl = struct.unpack_from('<IIQQII', fm, p)
        nm = fm[p + 0x20:p + 0x20 + nl].decode('utf-8', 'replace')
        files.append((dpath(par), nm, fo, sz))
        p += (0x20 + nl + 3) & ~3
    return data_off, files


def titlekey_variants(nca, tik_path):
    """Titlekey crypto 时 titlekek 版本号不一定取得到，枚举全部可用 titlekek 作为候选。"""
    if nca.rights == b'\0' * 16:
        return []
    blk = open(tik_path, 'rb').read()[0x180:0x190]
    out = []
    for i in range(0, 0x22):
        k = nca.keys.get('titlekek_%02x' % i)
        if not k:
            continue
        tk = AES.new(bytes.fromhex(k), AES.MODE_ECB).decrypt(blk)
        if tk not in out:
            out.append(tk)
    return out


def open_update(update, base_romfs, keys=None):
    keys, kp = B.pick_keys(keys)
    img = Image(base_romfs)
    r = B.BktrRomfs.__new__(B.BktrRomfs)
    r.nsp_ents = B.pfs0_list(update)
    r.tmp = []
    r.nca_path, r.tik = r._locate_nca(update, None)
    r.nca = B.Nca(r.nca_path, keys, r.tik)
    if isinstance(r.tik, str) and os.path.exists(r.tik):
        r.nca.alt_keys = titlekey_variants(r.nca, r.tik)
    idx = next(i for i in range(4) if r.nca.fsh[i][4] == 4)
    return Bktr2(r.nca, idx, img), img


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--update', required=True)
    ap.add_argument('--base-romfs', required=True)
    ap.add_argument('--outdir')
    ap.add_argument('--keys')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--get')
    ap.add_argument('--all', action='store_true')
    a = ap.parse_args()

    bdata, bfiles = parse_tables(0, Image(a.base_romfs).read)
    print('[i] 本体 romfs: data_off=%#x 文件 %d' % (bdata, len(bfiles)))
    bk, img = open_update(a.update, a.base_romfs, a.keys)
    pr = bk.patch_ranges()
    print('[i] 更新段 %d romfs_v=%#x entries=%d subs=%d patch 区间 %d 覆盖 %d B' %
          (bk.idx, bk.romfs, len(bk.entries), len(bk.subs), len(pr), sum(b - a2 for a2, b in pr)))
    data_off, files = parse_tables(bk.romfs, bk.read_v)
    print('[i] 更新 romfs 表: data_off=%#x 文件 %d' % (data_off, len(files)))
    ch = []
    for d, nm, fo, sz in files:
        s, e = bk.romfs + data_off + fo, bk.romfs + data_off + fo + sz
        if any(s < y and x < e for x, y in pr):
            ch.append((d, nm, fo, sz))
    print('[i] 与 patch 相交的文件 %d / %d' % (len(ch), len(files)))
    for d, nm, fo, sz in sorted(ch, key=lambda x: -x[3]):
        print('%12d  %s%s%s' % (sz, d, '/' if d else '', nm))
    if a.list:
        return 0
    tgt = [f for f in files if a.get is None or a.get.lower() in
           ((f[0] + '/' + f[1]).lower())]
    if a.outdir:
        os.makedirs(a.outdir, exist_ok=True)
    for d, nm, fo, sz in tgt:
        if not a.all and a.get is None and sz < 4096:
            continue
        blob = bk.read_v(bk.romfs + data_off + fo, sz)
        print('[o] %s%s%s  %d B  head=%s' % (d, '/' if d else '', nm, sz, blob[:8].hex()))
        if a.outdir:
            dst = os.path.join(a.outdir, d.lstrip('/'), nm) if d else os.path.join(a.outdir, nm)
            os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
            open(dst, 'wb').write(blob)
    return 0


if __name__ == '__main__':
    sys.exit(main())
