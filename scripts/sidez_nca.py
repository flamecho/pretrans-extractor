#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Blackish House sideZ -Retour- (NS) : 压缩 NCA(BKTR bucket-tree + LZ4) → RomFS。

判型（2026-10-23 立）：
  1) NCA3 / Titlekey crypto（key_area @0x300 全 0 ⇒ 内容密钥 = ticket titlekey）。
     titlekey = AES_ECB_dec(titlekek_[tik[0x285]-1], tik[0x180:0x190])。
  2) section1 的 FsHeader 有 CompressionInfo @+0x178 = {u64 TableOffset, u64 TableSize, BKTR}；
     TableOffset 相对 IVFC level5 起点；comp_type 3 = **标准 LZ4 block**（无帧头），0 = raw。
  3) 段 CTR：counter = be32(secno+1) ‖ 0u32 ‖ be64(绝对文件偏移/16)  ← 与 hactool 打印一致。
  4) IVFC 7 层（level0=master hash, level5=数据）。
  5) ★ RomFS 镜像无 "RomFS" 魔数（首字段即 header_size=0x50），别拿魔数当失败。

用法:
  python scripts/sidez_nca.py <nca> <out.json>            # 列文件
  python scripts/sidez_nca.py <nca> <out.json> --get <filter> <outdir>  # 按子串抽文件
"""
import sys, os, json, struct, hashlib
from Crypto.Cipher import AES
from Crypto.Util import Counter
import lz4.block

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import switch_nca as SN


def dec_header(path, keys):
    with open(path, 'rb') as f:
        return SN.xts_decrypt(bytes.fromhex(keys['header_key'][:32]),
                              bytes.fromhex(keys['header_key'][32:64]), 0, f.read(0x1200))


def titlekey_from_tik(nca_path, keys):
    hdr = dec_header(nca_path, keys)
    rights = hdr[0x230:0x240]
    kg = hdr[0x206]
    d = os.path.dirname(nca_path)
    for n in sorted(os.listdir(d)):
        if n.lower().endswith('.tik'):
            t = open(os.path.join(d, n), 'rb').read()
            if t[0x2A0:0x2B0] == rights:
                idx = t[0x285] - 1
                kk = bytes.fromhex(keys['titlekek_%02x' % idx])
                return AES.new(kk, AES.MODE_ECB).decrypt(t[0x180:0x190]), n
    raise SystemExit('no matching tik')


class Sec:
    """section 内按 CTR 随机读取（pos 为 section 内偏移）。"""

    def __init__(self, path, sec_off, secno, key):
        self.f = open(path, 'rb')
        self.sec_off = sec_off
        self.ctr_hi = (secno + 1) << 96          # be32(secno+1) 在最高 32 位
        self.key = key

    def read(self, pos, ln):
        base = self.ctr_hi + (self.sec_off + pos) // 16
        c = AES.new(self.key, AES.MODE_CTR, counter=Counter.new(128, initial_value=base))
        self.f.seek(self.sec_off + pos)
        return c.decrypt(self.f.read(ln))


class CompRomfs:
    def __init__(self, sec, lvl5, tab_off):
        self.sec, self.lvl5 = sec, lvl5
        T = lvl5 + tab_off
        h = sec.read(T, 0x10)
        self.nbucket = struct.unpack_from('<I', h, 4)[0]
        self.total = struct.unpack_from('<Q', h, 8)[0]
        ents = []
        for b in range(self.nbucket):
            b0 = T + 0x4000 + b * 0x4000
            bh = sec.read(b0, 0x10)
            bidx, cnt = struct.unpack_from('<II', bh, 0)
            if bidx != b or cnt == 0 or cnt > 0x3FF0 // 0x18:
                continue
            raw = sec.read(b0 + 0x10, cnt * 0x18)
            for k in range(cnt):
                ents.append(struct.unpack_from('<QQII', raw, k * 0x18))
        ents.sort()
        uniq = []
        for e in ents:
            if uniq and e[0] <= uniq[-1][0]:
                continue                        # 丢弃 zero-length / 重复 v
            uniq.append(e)
        self.ents = uniq
        self.cache = {}

    def _locate(self, off):
        lo, hi = 0, len(self.ents)
        while lo + 1 < hi:
            mid = (lo + hi) // 2
            if self.ents[mid][0] <= off:
                lo = mid
            else:
                hi = mid
        return lo

    def block(self, i):
        if i in self.cache:
            return self.cache[i]
        v, p, typ, sz = self.ents[i]
        end = self.ents[i + 1][0] if i + 1 < len(self.ents) else self.total
        n = end - v
        raw = self.sec.read(self.lvl5 + p, sz)
        data = raw[:n] if typ == 0 else lz4.block.decompress(raw, uncompressed_size=n)
        if len(self.cache) > 256:
            self.cache.clear()
        self.cache[i] = data
        return data

    def read(self, off, ln):
        out = bytearray()
        while ln > 0:
            i = self._locate(off)
            v = self.ents[i][0]
            end = self.ents[i + 1][0] if i + 1 < len(self.ents) else self.total
            if end <= off:                      # 重复 virtual offset ⇒ 跳过，避免死循环
                off = end
                continue
            b = self.block(i)
            s = off - v
            take = min(end - off, ln)
            out += b[s:s + take]
            off += take
            ln -= take
        return bytes(out)


def parse_romfs(v):
    hdr = v.read(0, 0x50)
    hs, dh_ofs, dh_sz, dm_ofs, dm_sz, fh_ofs, fh_sz, fm_ofs, fm_sz, fd_ofs = struct.unpack('<10Q', hdr)
    dm = v.read(dm_ofs, dm_sz)
    fm = v.read(fm_ofs, fm_sz)

    def dinfo(off):
        par, nxt, cd, cf, h, nl = struct.unpack_from('<IIIIII', dm, off)
        return par, nxt, cd, cf, dm[off + 0x18:off + 0x18 + nl].decode('utf-8', 'replace')

    def finfo(off):
        par, nxt, dofs, dsz, h, nl = struct.unpack_from('<IIQQII', fm, off)
        return par, nxt, dofs, dsz, fm[off + 0x20:off + 0x20 + nl].decode('utf-8', 'replace')

    files = []

    def walk(doff, prefix):
        _, _, cd, cf, _ = dinfo(doff)
        o = cf
        while o != 0xFFFFFFFF and o < len(fm):
            par, nxt, dofs, dsz, nm = finfo(o)
            files.append((prefix + nm, fd_ofs + dofs, dsz))
            o = nxt
        o = cd
        while o != 0xFFFFFFFF and o < len(dm):
            par, nxt, c2, f2, nm = dinfo(o)
            walk(o, prefix + nm + '/')
            o = nxt

    walk(0, '')
    return files, (hs, dh_ofs, dm_ofs, fh_ofs, fm_ofs, fd_ofs)


def open_nca(path, keyset='_sw/prod_fixed.keys'):
    keys = SN.load_keys(keyset)
    hdr = dec_header(path, keys)
    secs = []
    for i in range(4):
        e = hdr[0x240 + i * 0x10:0x250 + i * 0x10]
        ms = int.from_bytes(e[0:4], 'little')
        me = int.from_bytes(e[4:8], 'little')
        secs.append((ms * 0x200, me * 0x200))
    tk, tikname = titlekey_from_tik(path, keys)
    return hdr, secs, tk, keys


def main():
    nca = sys.argv[1]
    outjson = sys.argv[2]
    get_filter = None
    outdir = None
    if '--get' in sys.argv:
        k = sys.argv.index('--get')
        get_filter, outdir = sys.argv[k + 1], sys.argv[k + 2]

    hdr, secs, tk, keys = open_nca(nca)
    # 找带 CompressionInfo 的 IVFC 段
    target = None
    for i in range(4):
        if secs[i][1] == secs[i][0]:
            continue
        fh = hdr[0x400 + i * 0x200:0x600 + i * 0x200]
        if fh[0x08:0x0C] != b'IVFC':
            continue
        lvl5, lvl5sz = 0, 0
        for L in range(7):
            off = int.from_bytes(fh[0x18 + L * 0x18:0x20 + L * 0x18], 'little')
            sz = int.from_bytes(fh[0x20 + L * 0x18:0x28 + L * 0x18], 'little')
            if L == 5:
                lvl5, lvl5sz = off, sz
        tab_off = int.from_bytes(fh[0x178:0x180], 'little')
        tab_sz = int.from_bytes(fh[0x180:0x188], 'little')
        target = (i, lvl5, lvl5sz, tab_off, tab_sz)
        break
    if not target:
        raise SystemExit('no compressed IVFC section')
    i, lvl5, lvl5sz, tab_off, tab_sz = target
    print('[i] sec%d lvl5=0x%x size=0x%x table=0x%x size=0x%x' % (i, lvl5, lvl5sz, tab_off, tab_sz))
    print('[i] tableOffset+size == lvl5size ?', tab_off + tab_sz == lvl5sz)

    sec = Sec(nca, secs[i][0], i, tk)
    rom = CompRomfs(sec, lvl5, tab_off)
    print('[i] buckets=%d entries=%d total=0x%x' % (rom.nbucket, len(rom.ents), rom.total))
    files, info = parse_romfs(rom)
    print('[i] files=%d  tables=%s' % (len(files), info))
    json.dump([{'name': n, 'offset': o, 'size': s} for n, o, s in files],
              open(outjson, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    if get_filter:
        os.makedirs(outdir, exist_ok=True)
        n = 0
        for name, off, sz in files:
            if get_filter.lower() in name.lower():
                data = rom.read(off, sz)
                p = os.path.join(outdir, name.lstrip('/'))
                os.makedirs(os.path.dirname(p) or '.', exist_ok=True)
                open(p, 'wb').write(data)
                n += 1
        print('[+] extracted %d files' % n)


if __name__ == '__main__':
    main()
