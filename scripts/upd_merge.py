#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用「NS 官方更新（BKTR 差分）＋ 本体 NCA」→ 最新 romfs 文件 合并器。

适用：本体 NCA 是 **普通 romfs 或 LZ4 桶树压缩 romfs**，更新 NCA 是 **BKTR（crypt_type 4）**。
与 scripts/ukronia_upd.py 的区别：那边 base 吃**裸 romfs 镜像**，这边 base 直接吃 **NCA**
（内部按 fs 头判断压缩与否），省一次 2 GB 落盘。

三处必须注意的点（实测，勿照抄 bktr_romfs.py 的默认行为）：
  1) 更新的 relocation / subsection 表要用**普通段 CTR** 读：iv = hi<<64 | ((sec_start+v)>>4)，
     hi = LE-u64(fsh+0x140)。用 subsection 式会把 rel.total 读错 ⇒ 文件表解析崩。
  2) 本体文件偏移 = 镜像偏移（0 = romfs 头 = IVFC level5）；rel 里 is_patch=0 的 po 是**段内 FS 坐标**，
     镜像偏移 = po - l5。
  3) 更新档布局相对本体有**插入位移**，本体文件偏移 → 虚拟偏移必须由 rel 表反推
     （base 区间 [po-l5, +len) ↔ 虚拟区间 [vo, +len)）。

用法：
  python scripts/upd_merge.py <update.nsp|.nca> --base <base.nca> [--tik <update.tik>] [--base-tik <base.tik>]
        [--changed | --list | --get <子串> <outdir>]
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import lz4.block
from Crypto.Cipher import AES
from Crypto.Util import Counter

import bktr_romfs as B
from ukronia_upd import parse_romfs_image


class NcaImage:
    """把 NCA 的 romfs 段包装成「镜像偏移 0 = romfs 头」的随机读。支持普通段与 LZ4 桶树压缩段。"""

    def __init__(self, path, tik=None, keys=None):
        self.nca = B.Nca(path, keys, tik)
        n = self.nca
        self.idx = next(i for i in range(4) if n.fsh[i][3] == 3)
        self.sec = B.pick_romfs_reader(n, self.idx)
        F = n.fsh[self.idx]
        self.comp = struct.unpack_from('<QQ', F, 0x178)
        self.levels = [struct.unpack_from('<QQQ', F, 0x18 + i * 0x18) for i in range(6)]
        self.l5 = None
        for a, b, _ in self.levels:
            if b and self._raw(a, 8)[:1] == b'\x50':
                h = struct.unpack('<10Q', self._raw(a, 0x50))
                if h[0] == 0x50 and h[9] == 0x200:
                    self.l5 = a
                    break
        if self.l5 is None:
            raise SystemExit('base NCA 里定位不到 romfs 头')
        self.buckets = None
        if self.comp[0] or self.comp[1]:
            self._load_buckets()

    def _raw(self, off, n):
        return self.sec.read(off, n)

    def _load_buckets(self):
        tbl = self.l5 + self.comp[0]
        h = self._raw(tbl, 0x10)
        nb, total = struct.unpack_from('<IQ', h, 4)
        self.bucket_total = total
        self.ents = []
        for b in range(nb):
            bo = tbl + 0x4000 + b * 0x4000
            _, cnt, _e = struct.unpack_from('<IIQ', self._raw(bo, 0x10))
            raw = self._raw(bo + 0x10, cnt * 0x18)
            for k in range(len(raw) // 0x18):
                self.ents.append(struct.unpack_from('<QQII', raw, k * 0x18))
        self.ents.sort()
        self.cache = {}

    def _blk(self, i):
        if i in self.cache:
            return self.cache[i]
        v, p, t, sz = self.ents[i]
        end = self.ents[i + 1][0] if i + 1 < len(self.ents) else self.bucket_total
        n = end - v
        if t == 0:
            d = self._raw(self.l5 + p, n)
        else:
            d = lz4.block.decompress(self._raw(self.l5 + p, sz), uncompressed_size=n)
        if len(self.cache) > 256:
            self.cache.clear()
        self.cache[i] = d
        return d

    def read(self, off, n):
        if self.buckets is None:
            return self._raw(self.l5 + off, n)
        out = bytearray()
        while n > 0:
            lo, hi = 0, len(self.ents)
            while lo + 1 < hi:
                mid = (lo + hi) // 2
                if self.ents[mid][0] <= off:
                    lo = mid
                else:
                    hi = mid
            v = self.ents[lo][0]
            b = self._blk(lo)
            s = off - v
            take = min(len(b) - s, n)
            if take <= 0:
                raise RuntimeError('romfs 桶块读越界 off=%#x' % off)
            out += b[s:s + take]
            off += take
            n -= take
        return bytes(out)


class UpdMerge:
    def __init__(self, upd_path, base_nca, tik=None, base_tik=None, mode='plain'):
        keys, _ = B.pick_keys(None)
        self.keys = keys
        self.mode = mode
        self.base = NcaImage(base_nca, base_tik, keys)
        nca_path, tik = self._locate(upd_path, tik)
        n = B.Nca(nca_path, keys, tik)
        self.nca = n
        self.idx = next(i for i in range(4) if n.fsh[i][4] == 4)
        F, S = n.fsh[self.idx], n.secs[self.idx]
        self.sec = S
        self.hi = struct.unpack_from('<Q', F, 0x140)[0].to_bytes(8, 'big')
        self.key = n.keys_by_sec[self.idx]
        self.subs = [(0, 0)]
        try:
            self._read_subs(F)
        except Exception:
            self.subs = [(0, 0)]
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
        # ★ 关键：rel 的 po 用**更新档自己的 FS 坐标**，镜像偏移 = po - 更新档 level5。
        #   本体与更新的 level5 常常不等（本作 0x488000 vs 0x48c000），
        #   用本体 l5 去减会整体错 0x4000（合并出的 assets 直接解析成 0 个对象）。
        self.l5 = None
        for k in range(5, -1, -1):
            a, b, _s = struct.unpack_from('<QQQ', F, 0x18 + k * 0x18)
            if not b:
                continue
            try:
                h = self._rd(a, 0x50)
                if len(h) < 0x50:
                    continue
                v = struct.unpack_from('<10Q', h, 0)
                if v[0] == 0x50 and v[9] == 0x200:
                    self.l5 = a
                    break
            except Exception:
                continue
        if self.l5 is None:
            self.l5 = self.base.l5
        self.files, self.data_off = parse_romfs_image(self.base.read)

    def _read_subs(self, F):
        so, _ss = struct.unpack_from('<QQ', F, 0x120)
        _, nb, _tot = struct.unpack_from('<IIQ', self._rd(so, 0x10))
        subs = []
        for k in range(nb):
            bo = so + 0x4000 + k * 0x4000
            _, ne, _e = struct.unpack_from('<IIQ', self._rd(bo, 0x10))
            raw = self._rd(bo + 0x10, ne * 0x10)
            for j in range(len(raw) // 0x10):
                off, _8, ctr = struct.unpack_from('<QII', raw, j * 0x10)
                subs.append((off, ctr))
        subs.sort()
        if subs:
            self.subs = subs

    def _locate(self, path, tik):
        if path.lower().endswith('.nca'):
            return path, tik
        ents = B.pfs0_list(path)
        best, tp = None, tik
        with open(path, 'rb') as f:
            for name, off, size in ents:
                if name.endswith('.tik') and not tp:
                    tp = os.path.join(os.path.dirname(os.path.abspath(path)), name)
                    f.seek(off)
                    open(tp, 'wb').write(f.read(size))
                if name.endswith('.nca') and 'cnmt' not in name and (best is None or size > best[2]):
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
        return dst, tp

    def _rd(self, v, ln):
        """段内读：16 字节对齐取 counter，再切掉前缀 pad。mode=plain|sub。"""
        rel = v & ~0xF
        pad = v - rel
        n = ln + pad
        blk = (self.sec[0] + rel) >> 4
        ctr = 0
        if self.mode == 'sub':
            cur = self.subs[0]
            for s in self.subs:
                if s[0] <= rel:
                    cur = s
                else:
                    break
            ctr = cur[1]
        iv = int.from_bytes(self.hi + ctr.to_bytes(4, 'big') + (blk & 0xFFFFFFFF).to_bytes(4, 'big'), 'big')
        c = AES.new(self.key, AES.MODE_CTR, counter=Counter.new(128, initial_value=iv))
        self.nca.f.seek(self.sec[0] + rel)
        return c.decrypt(self.nca.f.read(n))[pad:]

    def patch_ranges(self):
        iv = []
        for i, e in enumerate(self.relocs):
            if e[2]:
                end = self.relocs[i + 1][0] if i + 1 < len(self.relocs) else self.total
                iv.append((e[0], end, e[1]))
        return iv

    def base_to_v(self, f_off):
        for i, e in enumerate(self.relocs):
            if e[2]:
                continue
            vo, po, _ = e
            bs = po - self.l5
            nxt = self.relocs[i + 1][0] if i + 1 < len(self.relocs) else self.total
            if bs <= f_off < bs + (nxt - vo):
                return vo + (f_off - bs)
        return None

    def changed(self):
        iv = self.patch_ranges()
        d0 = self.data_off
        out = []
        for rec in self.files:
            f = d0 + rec[2]
            v = self.base_to_v(f)
            if v is not None and any(v < z and a < v + rec[3] for a, z, _ in iv):
                out.append((rec, v))
        return out

    def base_entries(self):
        """[(vo, nxt, bs, be)]：base 条目对应的虚拟区间与本体偏移区间。"""
        out = []
        for i, e in enumerate(self.relocs):
            if e[2]:
                continue
            vo, po, _ = e
            bs = po - self.l5
            nxt = self.relocs[i + 1][0] if i + 1 < len(self.relocs) else self.total
            out.append((vo, nxt, bs, bs + (nxt - vo)))
        return out

    def merged(self, rec, v=None):
        """本体文件字节 + patch 区间覆写。

        坐标换算按「虚拟事件流」推进：base 条目给出 [vo,nxt) ↔ [bs,be)；夹在两条 base 条目之间的
        patch 区间是**就地替换**（等长接续），其本体起点 = 上一条 base 条目的末尾 bs_end。
        纯 patch 区间（前面没有 base 条目）无法定位，跳过并记日志。
        """
        _d, _n, fo, sz = rec
        f = self.data_off + fo
        out = bytearray(sz)
        events = []
        for vo, nxt, bs, bend in self.base_entries():
            events.append((vo, 0, nxt, bs, bend))
        for a, z, po in self.patch_ranges():
            events.append((a, 1, z, po, 0))
        events.sort(key=lambda e: (e[0], e[1]))
        cursor = None
        for v0, kind, v1, x0, x1 in events:
            if kind == 0:                      # base 条目
                cursor = x0 + (v1 - v0)
                s, t = max(f, x0), min(f + sz, x1)
                if t > s:
                    out[s - f:t - f] = self.base.read(s, t - s)
            else:                              # patch 区间
                if cursor is None:
                    continue
                bo0, ln = cursor, v1 - v0
                s, t = max(f, bo0), min(f + sz, bo0 + ln)
                if t > s:
                    out[s - f:t - f] = self._rd(x0 + (s - bo0), t - s)
                cursor = bo0 + ln
        return bytes(out)


def main():
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    upd = a[0]
    base = a[a.index('--base') + 1]
    tik = a[a.index('--tik') + 1] if '--tik' in a else None
    btik = a[a.index('--base-tik') + 1] if '--base-tik' in a else None
    mode = a[a.index('--mode') + 1] if '--mode' in a else 'plain'
    m = UpdMerge(upd, base, tik, btik, mode)
    print('[i] base romfs 文件 %d（l5=%#x, data_off=%#x, %s），CTR 模式=%s，subsection=%d' %
          (len(m.files), m.l5, m.data_off,
           '压缩桶树' if m.base.buckets is not None else '普通段', mode, len(m.subs)))
    print('[i] 更新段 %d  BKTR 虚拟总长=%#x  reloc=%d  patch 区间=%d' %
          (m.idx, m.total, len(m.relocs), len(m.patch_ranges())))
    ch = m.changed()
    if '--changed' in a:
        print('[i] 改动文件 %d / %d' % (len(ch), len(m.files)))
        for rec, v in sorted(ch, key=lambda x: -x[0][3]):
            print('%12d  %s%s%s  (v=%#x)' % (rec[3], rec[0], '/' if rec[0] else '', rec[1], v))
    if '--list' in a:
        for rec in m.files:
            print('%12d  %s%s%s' % (rec[3], rec[0], '/' if rec[0] else '', rec[1]))
    if '--get' in a:
        i = a.index('--get')
        key, outdir = a[i + 1], a[i + 2]
        hits = [(rec, v) for rec, v in ch if key.lower() in (rec[0] + '/' + rec[1]).lower()]
        if not hits:
            hits = [(r, m.base_to_v(m.data_off + r[2])) for r in m.files
                    if key.lower() in (r[0] + '/' + r[1]).lower()]
        os.makedirs(outdir, exist_ok=True)
        for rec, v in hits:
            data = m.merged(rec, v)
            if data is None:
                print('[!] %s 无映射，跳过' % rec[1])
                continue
            dst = os.path.join(outdir, rec[1])
            os.makedirs(os.path.dirname(dst), exist_ok=True) if os.path.dirname(dst) else None
            open(dst, 'wb').write(data)
            print('%-58s %10d -> %10d  %s' % ((rec[0] + '/' + rec[1]).lstrip('/'), rec[3], len(data), dst))
    return 0


if __name__ == '__main__':
    sys.exit(main())
