#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""泡沫のユークロニア 更新档（BKTR）→ 最新 romfs 文件 读取/合并。

为什么不用 scripts/bktr_romfs.py（两处不适配，均为本作实测）：
  1) 更新 NCA 的 relocation / subsection 两块表必须用**普通段 CTR** 读：
     iv = hi<<64 | ((sec_start+v)>>4)，hi = LE-u64(fsh+0x140)。
     用 bktr 的 subsection 4+4 拆分式会把 rel.total 读成 0x8e5dc2c0（真值 0x8e5e50c0），
     虚拟空间被截短，文件表定位随之失败。同坑见 `scripts/_archive/probes/bktr_audit.py --mode plain`。
  2) base 侧读口要按**裸 romfs 镜像偏移**算：镜像 0 = IVFC level6 起点 = FS 0x484000，
     而 rel 里的 base po 是 FS 坐标 ⇒ base_off = po + (v-vo) - 0x484000。
  3) 更新档的 romfs 布局相对本体有**插入位移**（本作 +0x8380），所以「文件虚拟位置」
     不能直接用 base 偏移代替，必须由 rel 表反推：base 区间 [po-l5, +len) ↔ 虚拟 [vo, +len)。

用法：
  python scripts/ukronia_upd.py <update.nsp|nca> --base <base.romfs> [--tik <tik>] --changed
  python scripts/ukronia_upd.py ... --list
  python scripts/ukronia_upd.py ... --get <子串> <outdir>        # 按更新档自己的文件表取（可能不可用）
  python scripts/ukronia_upd.py ... --getbase <子串> <outdir>    # 按「本体文件表 × 虚拟映射」取（推荐）
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from Crypto.Cipher import AES
from Crypto.Util import Counter

import bktr_romfs as B


def parse_romfs_image(read):
    """read(off, n) 给 romfs 镜像偏移；返回 (files[(dir,name,off,size)], data_off)。"""
    h = struct.unpack('<10Q', read(0, 0x50))
    if h[0] != 0x50:
        raise SystemExit('romfs 头无效')
    _, dh_o, dh_s, dm_o, dm_s, fh_o, fh_s, fm_o, fm_s, data_off = h
    dm = read(dm_o, dm_s)
    fm = read(fm_o, fm_s)
    dirs, p = {}, 0
    while p + 0x18 <= len(dm):
        par, sib, ch, fi, _h, nl = struct.unpack_from('<IIIIII', dm, p)
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
        par, sib, fo, sz, _h, nl = struct.unpack_from('<IIQQII', fm, p)
        if p + 0x20 + nl > len(fm):
            break
        files.append((dpath(par), fm[p + 0x20:p + 0x20 + nl].decode('utf-8', 'replace'), fo, sz))
        p += (0x20 + nl + 3) & ~3
    return files, data_off


class Upd:
    def __init__(self, path, base_romfs, tik=None):
        keys, _kp = B.pick_keys(None)
        nca_path, tik = self._locate(path, tik)
        self.nca = n = B.Nca(nca_path, keys, tik)
        self.idx = next(i for i in range(4) if n.fsh[i][4] == 4)
        F, S = n.fsh[self.idx], n.secs[self.idx]
        self.sec = S
        self.hi = struct.unpack_from('<Q', F, 0x140)[0].to_bytes(8, 'big')
        self.key = n.keys_by_sec[self.idx]
        relo, _ = struct.unpack_from('<QQ', F, 0x100)
        _, nb, self.total = struct.unpack_from('<IIQ', self._rd(relo, 0x10))
        self.relocs = []
        for k in range(nb):
            bo = relo + 0x4000 + k * 0x4000
            _, ne, _e = struct.unpack_from('<IIQ', self._rd(bo, 0x10))
            raw = self._rd(bo + 0x10, ne * 0x14)
            for j in range(len(raw) // 0x14):
                self.relocs.append(struct.unpack_from('<QQI', raw, j * 0x14))
        self.relocs.sort()
        self.base_path = base_romfs
        self.base = open(base_romfs, 'rb')
        self.base_size = os.path.getsize(base_romfs)
        self.l5 = self._find_l5()

    def _locate(self, path, tik):
        if path.lower().endswith('.nca'):
            return path, tik
        ents = B.pfs0_list(path)
        best, tikpath = None, tik
        with open(path, 'rb') as f:
            for name, off, size in ents:
                if name.endswith('.tik') and not tikpath:
                    tikpath = os.path.join(os.path.dirname(os.path.abspath(path)), name)
                    f.seek(off)
                    open(tikpath, 'wb').write(f.read(size))
                if name.endswith('.nca') and 'cnmt' not in name:
                    if best is None or size > best[2]:
                        best = (name, off, size)
        if best is None:
            raise SystemExit('nsp 里没有 nca')
        dst = os.path.join(os.path.dirname(os.path.abspath(path)), best[0])
        if not (os.path.exists(dst) and os.path.getsize(dst) == best[2]):
            with open(path, 'rb') as f, open(dst, 'wb') as g:
                f.seek(best[1])
                left = best[2]
                while left > 0:
                    b = f.read(min(1 << 24, left))
                    if not b:
                        break
                    g.write(b)
                    left -= len(b)
        return dst, tikpath

    def _rd(self, v, ln):
        iv = int.from_bytes(self.hi + ((self.sec[0] + v) >> 4).to_bytes(8, 'big'), 'big')
        c = AES.new(self.key, AES.MODE_CTR, counter=Counter.new(128, initial_value=iv))
        self.nca.f.seek(self.sec[0] + v)
        return c.decrypt(self.nca.f.read(ln))

    def _find_l5(self):
        F = self.nca.fsh[self.idx]
        for i in range(6):
            a, b, _ = struct.unpack_from('<QQQ', F, 0x18 + i * 0x18)
            if not b:
                continue
            try:
                h = struct.unpack('<10Q', self._rd(a, 0x50))
                if h[0] == 0x50 and h[9] == 0x200:
                    return a
            except Exception:
                pass
        raise SystemExit('定位不到 romfs 头')

    def _cover(self, v):
        lo, hi = 0, len(self.relocs)
        while lo + 1 < hi:
            mid = (lo + hi) // 2
            if self.relocs[mid][0] <= v:
                lo = mid
            else:
                hi = mid
        return self.relocs[lo], (self.relocs[lo + 1][0] if lo + 1 < len(self.relocs) else None)

    def vread(self, v, ln):
        out = bytearray()
        while ln > 0:
            cur, nxt = self._cover(v)
            vo, po, ip = cur
            k = min(ln, (nxt - v) if nxt else ln)
            if ip:
                out += self._rd(po + (v - vo), k)
            else:
                off = po + (v - vo) - self.l5
                self.base.seek(off)
                d = self.base.read(k)
                if len(d) < k:
                    d += b'\0' * (k - len(d))
                out += d
            v += k
            ln -= k
        return bytes(out)

    # -- 本体侧
    def base_files(self):
        f = open(self.base_path, 'rb')
        files, data_off = parse_romfs_image(lambda o, n: (f.seek(o), f.read(n))[1])
        f.close()
        self.b_data_off = data_off
        return files

    def base_to_v(self, f_off):
        """本体镜像偏移 → 更新档虚拟偏移（用 rel 表里的 base 区间反推插入位移）。"""
        for i, e in enumerate(self.relocs):
            if e[2]:
                continue
            vo, po, _ = e
            bs = po - self.l5
            nxt = self.relocs[i + 1][0] if i + 1 < len(self.relocs) else self.total
            be = bs + (nxt - vo)
            if bs <= f_off < be:
                return vo + (f_off - bs)
        return None

    def patch_ranges(self):
        iv = []
        for i, e in enumerate(self.relocs):
            if e[2]:
                end = self.relocs[i + 1][0] if i + 1 < len(self.relocs) else self.total
                iv.append((e[0], end))
        return iv

    def read_base_file(self, rec):
        _d, _n, fo, sz = rec
        v = self.base_to_v(self.b_data_off + fo)
        if v is None:
            return None, None
        return v, self.vread(v, sz)


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        raise SystemExit(__doc__)
    upd = a[0]
    base = a[a.index('--base') + 1]
    tik = a[a.index('--tik') + 1] if '--tik' in a else None
    u = Upd(upd, base, tik)
    files = u.base_files()
    print('[i] 更新段 %d  romfs_v=%#x  虚拟总长=%#x  reloc=%d' % (u.idx, u.l5, u.total, len(u.relocs)))
    print('[i] 本体 romfs 文件 %d，镜像 %d B' % (len(files), u.base_size))
    iv = u.patch_ranges()
    d0 = u.b_data_off
    changed = []
    for r in files:
        v = u.base_to_v(d0 + r[2])
        if v is not None and any(v < y and x < v + r[3] for x, y in iv):
            changed.append(r)
    if '--changed' in a:
        print('[i] patch 区间 %d 个，改动文件 %d / %d' % (len(iv), len(changed), len(files)))
        for d, n, fo, sz in sorted(changed, key=lambda x: -x[3]):
            print('%12d  %s%s%s' % (sz, d, '/' if d else '', n))
    if '--list' in a:
        for d, n, fo, sz in sorted(files, key=lambda x: (x[0], x[1])):
            print('%12d  %s%s%s' % (sz, d, '/' if d else '', n))
    if '--getbase' in a:
        i = a.index('--getbase')
        key, outdir = a[i + 1], a[i + 2]
        hits = [f for f in files if key.lower() in (f[0] + '/' + f[1]).lower()]
        if not hits:
            print('没匹配到:', key)
            return 1
        os.makedirs(outdir, exist_ok=True)
        for d, n, fo, sz in hits:
            v, data = u.read_base_file((d, n, fo, sz))
            if data is None:
                print('[!] %s 无映射（整文件落在 patch 区间）' % n)
                continue
            dst = os.path.join(outdir, n)
            open(dst, 'wb').write(data)
            print('%-58s %10d B  v=%#x -> %s' % ((d + '/' + n).lstrip('/'), len(data), v, dst))
    return 0


if __name__ == '__main__':
    sys.exit(main())
