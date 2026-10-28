#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NS 更新档「Patch RomFS / BKTR」读取器（不依赖 hactool，可直接读 .nsp/.nca）。

背景：更新 NCA 的 romfs 段 crypt_type = 4 (BKTR)，段内不是完整 romfs，而是
「相对 base romfs 的差分」：虚拟地址空间 = base romfs 全长（本例 4.89 GB），
其中 unchanged 区间映射到 base romfs 同偏移处，changed 区间映射到本段物理数据。
所以**必须有 base**，否则 romfs 头/目录表都读不全（头本身就能跨 patch/base 边界）。

段物理布局（实测 スチームプリズン 1.0.1）：
  0x000000                     IVFC level 数据（hash 层 + 本体数据）
  rel_header.offset (0xDFAE00) relocation block   0x8000
  sub_header.offset (0xE02E00) subsection block   0x8000   ← 到段尾
FS 头（0x600 + n*0x200）里：
  +0x00 u8*4 : ver, _, part_type, fs_type(3=ROMFS), +0x04 crypt_type(4=BKTR)
  +0x08      : IVFC 头（magic "IVFC"，level_count @+0x14=7，level @+0x18 每项 0x18：
               {u64 logical_offset, u64 hash_data_size, u64 block_size}，master_hash @+0xC0）
  +0x100     : rel header {u64 offset, u64 size, u32 magic "BKTR", u32 ver, u32 num_entries, u32}
  +0x120     : sub header 同上
  +0x140     : section CTR 高 8 字节（u64 小端读出 → 按大端写进 counter）

两种块：
  relocation block : {u32 _, u32 num_buckets, u64 total_size, u64 virt_offsets[0x7FE]} + buckets
       bucket @+0x4000 起，每桶 0x4000：{u32 _, u32 num_entries, u64 virt_end, entry[]}
       entry = {u64 virt_offset, u64 phys_offset, u32 is_patch}   (0x14, packed)
  subsection block : {u32 _, u32 num_buckets, u64 total_size, u64 phys_offsets[0x7FE]} + buckets
       entry = {u64 offset, u32 _, u32 ctr_val}   (0x10)
       → 段内物理读的 counter = ctr_hi(8) | ctr_val(u32 BE) | ((nca绝对偏移>>4)&0xFFFFFFFF)

用法：
  python scripts/bktr_romfs.py <update.nca|update.nsp> --base <base.nca|base.romfs> --list
  python scripts/bktr_romfs.py <update.nca|update.nsp> --base ... --get <路径子串> [--out DIR]
  python scripts/bktr_romfs.py <update.nca> --info          # 只看 BKTR 结构，不需要 base
可选：--keys <keys文件>（默认 _sw/merged.keys 或 _sw/prod_fixed.keys）
      --tik <tik文件>       Titlekey crypto 时指定（nsp 内会自动找）
"""
import os
import struct
import sys

from Crypto.Cipher import AES
from Crypto.Util import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MASK = (1 << 128) - 1


# ---------------------------------------------------------------- 基础工具
def alpha(t):
    c = t >> 127
    t = (t << 1) & MASK
    if c:
        t ^= 0x87
    return t


def xts_decrypt(k1, k2, data, base_off=0):
    """Nintendo XTS：tweak 反转字节序（同 sector 内 T ← rev(α(rev(T)))）。"""
    ek2 = AES.new(k2, AES.MODE_ECB)
    dk1 = AES.new(k1, AES.MODE_ECB)

    def rev(x):
        return int.from_bytes(x.to_bytes(16, 'big'), 'little')

    out = bytearray()
    s0 = base_off // 0x200
    for i in range(0, len(data), 0x200):
        sec = data[i:i + 0x200]
        tweak = int.from_bytes(ek2.encrypt((s0 + i // 0x200).to_bytes(16, 'big')), 'big')
        buf = bytearray()
        for j in range(0, len(sec), 0x10):
            tb = tweak.to_bytes(16, 'big')
            blk = sec[j:j + 0x10]
            p = dk1.decrypt(bytes(x ^ y for x, y in zip(blk, tb)))
            buf += bytes(m ^ n for m, n in zip(p, tb))
            tweak = rev(alpha(rev(tweak)))
        out += buf
    return bytes(out)


def load_keys(path):
    d = {}
    for line in open(path, encoding='utf-8', errors='ignore'):
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        d[k.strip()] = v.strip()
    return d


def pick_keys(explicit):
    for p in [explicit, os.path.join(ROOT, '_sw', 'merged.keys'), os.path.join(ROOT, '_sw', 'prod_fixed.keys')]:
        if p and os.path.exists(p):
            return load_keys(p), p
    raise SystemExit('找不到 keys 文件（_sw/merged.keys）')


def pfs0_list(path):
    """返回 [(name, abs_off, size)]；非 PFS0 返回 []。"""
    f = open(path, 'rb')
    h = f.read(0x10)
    if len(h) < 0x10 or h[:4] != b'PFS0':
        f.close()
        return []
    n, strsz = struct.unpack_from('<II', h, 4)
    ents = [struct.unpack('<QQII', f.read(0x18)) for _ in range(n)]
    st = f.read(strsz)
    base = 0x10 + n * 0x18 + strsz
    f.close()
    return [(st[so:st.index(b'\0', so)].decode('utf-8', 'replace'), base + off, size) for off, size, so, _ in ents]


def ctr_split(iv16):
    return int.from_bytes(iv16, 'big')


# ---------------------------------------------------------------- NCA
class Nca:
    def __init__(self, path, keys, tik_path=None, off=0, size=None):
        self.path, self.keys, self.off = path, keys, off
        self.f = open(path, 'rb')
        self.f.seek(off)
        raw = self.f.read(0x4000)
        hk = bytes.fromhex(keys['header_key'])
        self.hdr = xts_decrypt(hk[:16], hk[16:], raw[:0x1200])
        h = self.hdr
        assert h[0x200:0x204] == b'NCA3', '不是 NCA3'
        self.nca_size = struct.unpack_from('<Q', h, 0x208)[0]
        self.title_id = struct.unpack_from('<Q', h, 0x210)[0]
        self.crypt_type = h[0x206]
        self.kaek_ind = h[0x207]
        self.crypto_type2 = h[0x220]
        self.rights = h[0x230:0x240]
        self.key_area = h[0x300:0x340]
        self.secs = []
        for i in range(4):
            st, en = struct.unpack_from('<II', h, 0x240 + i * 0x10)
            self.secs.append((st * 0x200, en * 0x200))
        self.fsh = [h[0x400 + i * 0x200:0x600 + i * 0x200] for i in range(4)]
        self.keys_by_sec = self._section_keys(tik_path)
        self.alt_keys = self._alt_keys(tik_path)

    def _alt_keys(self, tik_path):
        """标准加密时 key_area 的 4 个块都要留着：段号↔key_area 下标并不总是 i==i。"""
        if self.rights != b'\0' * 16:
            k = self.keys_by_sec.get(0)
            return [k] if k else []
        kak = self.keys.get('key_area_key_application_%02x' % (self.crypto_type2 - 1))
        if not kak:
            return []
        kak = bytes.fromhex(kak)
        out = []
        for i in range(4):
            blk = self.key_area[i * 16:i * 16 + 16]
            if blk != b'\0' * 16:
                out.append(AES.new(kak, AES.MODE_ECB).decrypt(blk))
        return out

    # -- 内容密钥：Titlekey crypto 直接用 titlekey；Standard 用 key_area
    def _section_keys(self, tik_path):
        out = {}
        if self.rights != b'\0' * 16:
            tk = self._titlekey(tik_path)
            for i in range(4):
                out[i] = tk
            return out
        kak_name = 'key_area_key_application_%02x' % max(self.kaek_ind, self.crypto_type2 - 1)
        kak = self.keys.get(kak_name)
        if not kak:
            return out
        kak = bytes.fromhex(kak)
        for i in range(4):
            blk = self.key_area[i * 16:i * 16 + 16]
            if blk != b'\0' * 16:
                out[i] = AES.new(kak, AES.MODE_ECB).decrypt(blk)
        return out

    def _titlekey(self, tik_path):
        if not tik_path:
            cand = os.path.join(os.path.dirname(os.path.abspath(self.path)), self.rights.hex() + '.tik')
            tik_path = cand if os.path.exists(cand) else None
        if not tik_path:
            raise SystemExit('需要 .tik（Titlekey crypto），用 --tik 指定')
        blk = open(tik_path, 'rb').read()[0x180:0x190]
        for rev in (self.crypto_type2 - 1, self.crypto_type2, 0x0a, 0x0b):
            k = self.keys.get('titlekek_%02x' % rev)
            if k:
                cand = AES.new(bytes.fromhex(k), AES.MODE_ECB).decrypt(blk)
                return cand
        raise SystemExit('没有对应的 titlekek')

    # -- 段读（CTR / BKTR 物理）
    def _read_raw(self, abs_off, n):
        self.f.seek(self.off + abs_off)
        return self.f.read(n)

    def _ctr(self, key, hi, abs_off, n, ctr_val=None):
        rel = abs_off & ~0xF
        pad = abs_off - rel
        body = self._read_raw(rel, ((n + pad + 15) // 16) * 16)
        if ctr_val is None:
            iv = hi + (rel >> 4).to_bytes(8, 'big')
        else:
            iv = hi + ctr_val.to_bytes(4, 'big') + ((rel >> 4) & 0xFFFFFFFF).to_bytes(4, 'big')
        p = AES.new(key, AES.MODE_CTR, counter=Counter.new(128, initial_value=int.from_bytes(iv, 'big'))).decrypt(body)
        return p[pad:pad + n]

    def section_size(self, i):
        st, en = self.secs[i]
        return en - st

    def sec_hi(self, i):
        return int.from_bytes(self.fsh[i][0x140:0x148], 'little').to_bytes(8, 'big')


class SecReader:
    """段内（段相对）随机读；BKTR 段用 subsection 的 ctr_val。"""

    def __init__(self, nca, idx, subs=None, key=None):
        self.nca, self.idx = nca, idx
        self.base, self.end = nca.secs[idx]
        self.key = key or nca.keys_by_sec.get(idx)
        self.hi = nca.sec_hi(idx)
        self.subs = subs or [(0, 0)]

    def _sub(self, rel):
        cur = self.subs[0]
        for s in self.subs:
            if s[0] <= rel:
                cur = s
            else:
                break
        return cur[1]

    def read(self, rel, n):
        n = max(0, min(n, self.end - self.base - rel))
        if n == 0:
            return b''
        if self.key is None:
            raise SystemExit('段 %d 没有内容密钥' % self.idx)
        if self.nca.fsh[self.idx][4] == 4:      # BKTR
            return self.nca._ctr(self.key, self.hi, self.base + rel, n, self._sub(rel))
        return self.nca._ctr(self.key, self.hi, self.base + rel, n)

    def __len__(self):
        return self.end - self.base


def xci_ncas(path):
    """返回 XCI 里所有 NCA 的 [(size, name, abs_off)]；扫前 64MB 的 HFS0，取 Σsize 最大且含 .nca 的那个。"""
    import os as _os
    fs = _os.path.getsize(path)
    with open(path, 'rb') as f:
        head = f.read(64 << 20)
    best, bestsum = None, -1
    i = 0
    while True:
        j = head.find(b'HFS0', i)
        if j < 0:
            break
        i = j + 4
        num, strsz = struct.unpack_from('<II', head, j + 4)
        if num > 4096 or strsz > (1 << 20) or j + 0x10 + num * 0x40 + strsz > len(head):
            continue
        st = j + 0x10 + num * 0x40
        names = head[st:st + strsz].split(b'\x00')[:num]
        if not any(n.endswith(b'.nca') for n in names):
            continue
        sizes = [struct.unpack_from('<Q', head, j + 0x10 + k * 0x40 + 8)[0] for k in range(num)]
        if sum(sizes) > bestsum:
            bestsum, best = sum(sizes), (j, num, strsz, names, sizes)
    if not best:
        raise SystemExit('XCI 里找不到 secure 分区')
    j, num, strsz, names, sizes = best
    # ★nsz 重打包的 XCI：HFS0 头与数据区不连续（头被挪到数据前 0x8000 处）。
    #   两个候选都试，调用方用「解出来是不是 NCA3」自证。
    starts = [fs - bestsum, (j + 0x10 + num * 0x40 + strsz + 0x1FF) & ~0x1FF]
    out = []
    for d0 in starts:
        if d0 < 0 or d0 >= fs:
            continue
        cur = d0
        for k in range(num):
            nm = names[k].decode('utf-8', 'replace')
            if nm.endswith('.nca'):
                out.append((sizes[k], nm, cur))
            cur += sizes[k]
    return out


def pick_romfs_reader(nca, idx):
    """段的 key_area 下标不一定等于段号：用「该段 romfs 头 header_size==0x50」自证。"""
    fsh = nca.fsh[idx]
    lc = struct.unpack_from('<I', fsh, 0x14)[0]
    levels = [struct.unpack_from('<QQQ', fsh, 0x18 + i * 0x18) for i in range(max(1, min(lc, 7)))]
    cands = []
    k0 = nca.keys_by_sec.get(idx)
    if k0:
        cands.append(k0)
    for k in nca.alt_keys:
        if k not in cands:
            cands.append(k)
    best = None
    for k in cands:
        r = SecReader(nca, idx, None, k)
        for lo, sz, _ in [l for l in levels if l[1]]:
            try:
                if struct.unpack('<Q', r.read(lo, 8))[0] == 0x50:
                    return r
            except Exception:
                pass
        best = best or r
    if best is None:
        raise SystemExit('base romfs 段密钥未确定')
    return best


class PlainReader:
    """裸 romfs 镜像（--base x.romfs）或 Base NCA 的 romfs 段。"""

    def __init__(self, path, keys=None, tik=None):
        self.tmp = []
        self.nca = None
        ents = pfs0_list(path)                     # base 也可以是 nsp：直接吃里面的最大 NCA
        if ents:
            if not tik:
                for name, off, size in ents:
                    if name.endswith('.tik'):
                        tik = self._tmp_extract(path, off, size, name)
                        break
            cand = [(size, name, off) for name, off, size in ents
                    if name.endswith('.nca') and 'cnmt' not in name]
            size, name, off = max(cand)
            n = Nca(path, keys, tik, off=off)
            idx = next((i for i in range(4) if n.fsh[i][3] == 3), None)
            if idx is None:
                raise SystemExit('base NCA 里没有 ROMFS 段')
            self.nca = pick_romfs_reader(n, idx)
            self.path = path
            return
        self.raw = open(path, 'rb')
        hd = self.raw.read(0x200)
        if hd[0x100:0x104] == b'HEAD':               # XCI：扫 secure HFS0（重打包件的 rom_area 常不可信）
            n = None
            for _sz, _nm, off in sorted(xci_ncas(path), reverse=True):
                try:
                    n = Nca(path, keys, tik, off=off)
                    break
                except AssertionError:
                    continue
            if n is None:
                raise SystemExit('XCI 里定不到 NCA 起点（试试先 xci_hfs0.py 抽出来）')
            idx = next((i for i in range(4) if n.fsh[i][3] == 3), None)
            if idx is None:
                raise SystemExit('base XCI 里没有 ROMFS 段')
            self.nca = pick_romfs_reader(n, idx)
            self.path = path
            return
        mag = hd + self.raw.read(4)
        if mag[0x200:0x204] == b'NCA3':
            n = Nca(path, keys, tik)
            idx = next((i for i in range(4) if n.fsh[i][3] == 3), None)
            if idx is None:
                raise SystemExit('base NCA 里没有 ROMFS 段')
            self.nca = pick_romfs_reader(n, idx)

    def _tmp_extract(self, src, off, size, name):
        import tempfile
        dst = os.path.join(tempfile.gettempdir(), '_bktr_base_' + name)
        with open(src, 'rb') as f, open(dst, 'wb') as g:
            f.seek(off)
            left = size
            while left > 0:
                b = f.read(min(1 << 24, left))
                if not b:
                    break
                g.write(b)
                left -= len(b)
        self.tmp.append(dst)
        return dst

    def read(self, off, n):
        if self.nca:
            return self.nca.read(off, n)
        self.raw.seek(off)
        return self.raw.read(n)


# ---------------------------------------------------------------- BKTR
class Bktr:
    def __init__(self, nca, idx, base=None):
        self.nca, self.idx, self.base = nca, idx, base
        fsh = nca.fsh[idx]
        self.level_count = struct.unpack_from('<I', fsh, 0x14)[0]
        self.levels = []
        for i in range(min(self.level_count, 7)):
            o = 0x18 + i * 0x18
            lo, sz, blk = struct.unpack_from('<QQQ', fsh, o)
            self.levels.append((lo, sz, blk))
        self.rel = self._hdr(0x100, fsh)
        self.sub = self._hdr(0x120, fsh)
        self.subs = [(0, 0)]
        self.relocs = []
        self.reader = SecReader(nca, idx, self.subs)   # 与 self.subs 共享同一个 list
        self._read_subs()
        self._read_relocs()
        # romfs 起点 = level 的 logical_offset（★虚拟偏移），用 header_size==0x50 自证
        self.romfs = None
        order = [l for l in reversed(self.levels) if l[1] and l[0]] + [l for l in self.levels if l[1] and l[0]]
        for lo, sz, _ in order:
            try:
                if struct.unpack('<Q', self.vread(lo, 8))[0] == 0x50:
                    self.romfs = lo
                    break
            except SystemExit:
                continue

    @staticmethod
    def _hdr(off, fsh):
        o, sz, mg, ver, ne, _ = struct.unpack_from('<QQIIII', fsh, off)
        return dict(offset=o, size=sz, magic=mg.to_bytes(4, 'little'), ver=ver, num=ne)

    def _read_subs(self):
        b = self.sub['offset']
        _, nb, _tot = struct.unpack_from('<IIQ', self.reader.read(b, 0x10))
        subs = []
        for k in range(nb):
            bo = b + 0x4000 + k * 0x4000
            _, ne, _end = struct.unpack_from('<IIQ', self.reader.read(bo, 0x10))
            for j in range(ne):
                off, _8, ctr = struct.unpack_from('<QII', self.reader.read(bo + 0x10 + j * 0x10, 0x10))
                subs.append((off, ctr))
        subs.sort()
        if not subs:
            subs = [(0, 0)]
        self.subs[:] = subs

    def _read_relocs(self):
        b = self.rel['offset']
        _, nb, _tot = struct.unpack_from('<IIQ', self.reader.read(b, 0x10))
        for k in range(nb):
            bo = b + 0x4000 + k * 0x4000
            _, ne, _end = struct.unpack_from('<IIQ', self.reader.read(bo, 0x10))
            for j in range(ne):
                vo, po, ip = struct.unpack_from('<QQI', self.reader.read(bo + 0x10 + j * 0x14, 0x14))
                self.relocs.append((vo, po, ip))
        self.relocs.sort()

    def read_phys(self, rel, n):
        return self.reader.read(rel, n)

    def map_of(self, v):
        cur = None
        for e in self.relocs:
            if e[0] <= v:
                cur = e
            else:
                break
        if cur is None:
            return None
        return cur[1] + (v - cur[0]), cur[2]

    def vread(self, v, n):
        """虚拟读：patch 区间 → 段物理数据；base 区间 → base romfs 同偏移。"""
        out = bytearray()
        while n > 0:
            m = self.map_of(v)
            if m is None:
                raise SystemExit('虚拟偏移 %#x 没有映射' % v)
            po, is_patch = m
            nxt = None
            for e in self.relocs:
                if e[0] > v:
                    nxt = e[0]
                    break
            k = min(n, (nxt - v) if nxt else n)
            if is_patch:
                out += self.read_phys(po, k)
            else:
                if self.base is None:
                    raise SystemExit('需要 base（虚拟 %#x 落在 base 区间）' % v)
                out += self.base.read(po, k)
            v += k
            n -= k
        return bytes(out)


class BktrRomfs:
    def __init__(self, update_path, base_path, keys, tik=None):
        self.nsp_ents = pfs0_list(update_path)
        self.tmp = []
        self.nca_path, self.tik = self._locate_nca(update_path, tik)
        self.nca = Nca(self.nca_path, keys, self.tik)
        idx = next((i for i in range(4) if self.nca.fsh[i][4] == 4), None)
        if idx is None:
            raise SystemExit('这个 NCA 里没有 BKTR(Patch RomFS) 段')
        self.idx = idx
        self.base = PlainReader(base_path, keys, tik) if base_path else None
        self.bk = Bktr(self.nca, idx, self.base)
        if self.bk.romfs is None:
            raise SystemExit('定位不到虚拟 romfs 头')
        self._load()

    def _locate_nca(self, path, tik):
        if path.lower().endswith('.nca'):
            return path, tik
        best = None
        t = tik
        for name, off, size in self.nsp_ents:
            if name.endswith('.tik') and not t:
                t = self._extract(path, off, size, name)
            if name.endswith('.nca') and 'cnmt' not in name:
                if best is None or size > best[2]:
                    best = (name, off, size)
        if best is None:
            raise SystemExit('nsp 里没有 nca')
        return self._extract(path, best[1], best[2], best[0]), t

    def _extract(self, src, off, size, name):
        import tempfile
        dst = os.path.join(tempfile.gettempdir(), '_bktr_' + name)
        if os.path.exists(dst) and os.path.getsize(dst) == size:
            self.tmp.append(dst)
            return dst
        with open(src, 'rb') as f:
            f.seek(off)
            left = size
            with open(dst, 'wb') as g:
                while left > 0:
                    b = f.read(min(1 << 24, left))
                    if not b:
                        break
                    g.write(b)
                    left -= len(b)
        self.tmp.append(dst)
        return dst

    def vread(self, v, n):
        return self.bk.vread(v, n)

    # -- romfs
    def _load(self):
        h = struct.unpack_from('<10Q', self.vread(self.bk.romfs, 0x50))
        (self.hdr_size, self.dh_off, self.dh_sz, self.dm_off, self.dm_sz,
         self.fh_off, self.fh_sz, self.fm_off, self.fm_sz, self.data_off) = h
        if self.hdr_size != 0x50:
            raise SystemExit('虚拟 romfs 头无效')
        dm = self.vread(self.bk.romfs + self.dm_off, self.dm_sz)
        fm = self.vread(self.bk.romfs + self.fm_off, self.fm_sz)
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

        self.files = []
        p = 0
        while p + 0x20 <= len(fm):
            par, sib, fo, sz, hsh, nl = struct.unpack_from('<IIQQII', fm, p)
            nm = fm[p + 0x20:p + 0x20 + nl].decode('utf-8', 'replace')
            self.files.append((dpath(par), nm, fo, sz))
            p += (0x20 + nl + 3) & ~3

    def patch_ranges(self):
        iv, n = [], len(self.bk.relocs)
        for i, e in enumerate(self.bk.relocs):
            if e[2]:
                end = self.bk.relocs[i + 1][0] if i + 1 < n else self.bk.relocs[-1][0] + (1 << 40)
                iv.append((e[0], end))
        return iv

    def changed(self):
        iv = self.patch_ranges()
        d0 = self.bk.romfs + self.data_off
        out = []
        for rec in self.files:
            a, z = d0 + rec[2], d0 + rec[2] + rec[3]
            if any(a < y and x < z for x, y in iv):
                out.append(rec)
        return out

    def open_file(self, rec):
        d, n, fo, sz = rec
        return self.vread(self.bk.romfs + self.data_off + fo, sz)


def main():
    import argparse
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('target', help='update .nca 或 .nsp')
    ap.add_argument('--base', help='base .nca 或裸 base.romfs')
    ap.add_argument('--keys')
    ap.add_argument('--tik')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--info', action='store_true')
    ap.add_argument('--changed', action='store_true', help='只列本次更新真正改动的文件')
    ap.add_argument('--get', nargs=2, metavar=('KEY', 'OUTDIR'))
    a = ap.parse_args()

    keys, kp = pick_keys(a.keys)
    print('keys:', kp)
    r = BktrRomfs(a.target, a.base, keys, a.tik)
    bk = r.bk
    print('NCA %s  sec%d  BKTR  romfs_v=%#x  文件 %d' %
          (os.path.basename(r.nca_path), r.idx, bk.romfs, len(r.files)))
    if a.info or a.list:
        print('  relocation : off=%#x size=%#x 段内 entry=%d 虚拟总长=%#x' %
              (bk.rel['offset'], bk.rel['size'], len(bk.relocs), bk.relocs[-1][0] if bk.relocs else 0))
        print('  subsection : off=%#x size=%#x ctr 表=%d' % (bk.sub['offset'], bk.sub['size'], len(bk.subs)))
        print('  levels     : ' + ' '.join('%#x/%#x' % (x, y) for x, y, _ in bk.levels))
    if a.changed:
        ch = r.changed()
        print('patch 区间 %d 个，改动文件 %d / %d' % (len(r.patch_ranges()), len(ch), len(r.files)))
        for d, n, fo, sz in sorted(ch, key=lambda x: -x[3]):
            print('%12d  %s%s%s' % (sz, d, '/' if d else '', n))
        return 0
    if a.list or a.info:
        for d, n, fo, sz in sorted(r.files, key=lambda x: (x[0], x[1])):
            print('%12d  %s%s%s' % (sz, d, '/' if d else '', n))
        return 0
    if a.get:
        key, outdir = a.get
        hits = [f for f in r.files if key.lower() in (f[0] + '/' + f[1]).lower()]
        if not hits:
            print('没匹配到:', key)
            return 1
        os.makedirs(outdir, exist_ok=True)
        for d, n, fo, sz in hits:
            data = r.open_file((d, n, fo, sz))
            dst = os.path.join(outdir, n)
            open(dst, 'wb').write(data)
            print('%-60s %10d B -> %s' % ((d + '/' + n).lstrip('/'), len(data), dst))
        return 0
    return 0


if __name__ == '__main__':
    sys.exit(main())
