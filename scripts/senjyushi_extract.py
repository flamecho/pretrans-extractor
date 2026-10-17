#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""千銃士:Rhodoknight (NS) 解包 —— 压缩 NCA (LZ4 bucket-tree) → RomFS → 文件。

★ 本作关键（2026-10-16 确立，通用结论见 skill）：
  1) NCA 头 XTS tweak **字节序反转**（见 scripts/switch_nca.py）。
  2) 本 NCA 的 section1(RomFS, AesCtr) 是**压缩 NCA**：
     fs header CompressionInfo(@+0x178) = {u64 TableOffset, u64 TableSize, BucketTreeHeader}。
     **TableOffset 相对「section 的 DATA 层(IVFC level5)起点」**，不是 section 起点的绝对偏移。
     本例：level5 @0x1894000，TableOffset 0x2e9144000 → 表在 section 0x2EAA58000(=level5+TableOffset)。
     TableOffset+TableSize == level5 尺寸（自洽判据）。
  3) 表结构（桶树）：@0x00 u32 pad; @0x04 u32 bucket_count; @0x08 u64 total_uncompressed;
     @0x10 bucket_count × u64 base_offsets; 桶从 @0x4000 起，每桶 0x4000：
       {u32 idx, u32 entry_count, u64 end_offset} + entry_count × 0x18 条目。
     条目 = {u64 virtual_offset, u64 physical_offset(相对 level5 起点), u32 comp_type, u32 comp_size}。
     comp_type: 0=未压缩, 3=LZ4(块格式)；physical 按 0x10 对齐，故**必须用 comp_size 截取**（否则 LZ4 报 corrupt）。
  4) 块大小 0x10000；首块 0x200(raw)。解压总长 == total_uncompressed == RomFS 镜像大小。

用法: python scripts/senjyushi_extract.py <nca> [--list] [--outdir=<dir>] [--keyset=<keys>]
"""
import sys, os, struct, json
import lz4.block
from Crypto.Cipher import AES
from Crypto.Util import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import switch_nca as SN

SEC1_OFF = 0x1c000          # section 1 file offset
SEC1_SIZE = 0x2eae94000
SEC1_CTR = bytes.fromhex('00000002000000000000000000001C00')
TITLEKEY = bytes.fromhex('1c21bce053719f696dcf31bbe5c2e925')


class NcaReader:
    """按 CTR 解密 NCA section1 的物理字节。"""

    def __init__(self, path, sec_off=SEC1_OFF, ctr=SEC1_CTR, key=TITLEKEY):
        self.f = open(path, 'rb')
        self.sec_off = sec_off
        self.ctr0 = ctr
        self.key = key

    def read(self, pos, ln):
        c = AES.new(self.key, AES.MODE_CTR,
                    counter=Counter.new(128, initial_value=int.from_bytes(self.ctr0, 'big') + pos // 16))
        self.f.seek(self.sec_off + pos)
        return c.decrypt(self.f.read(ln))


def parse_buckets(rd):
    """解析压缩表，返回 (entries, total)。entries = [(v,p,type,csize), ...] 按 v 升序。"""
    T = 0x1894000 + 0x2e9144000          # level5 起点 + TableOffset
    hdr = rd.read(T, 0x10)
    nbucket = struct.unpack_from('<I', hdr, 4)[0]
    total = struct.unpack_from('<Q', hdr, 8)[0]
    ents = []
    for b in range(nbucket):
        b0 = T + 0x4000 + b * 0x4000
        bh = rd.read(b0, 0x10)
        cnt = struct.unpack_from('<I', bh, 4)[0]
        raw = rd.read(b0 + 0x10, cnt * 0x18)
        for k in range(cnt):
            v, p, typ, sz = struct.unpack_from('<QQII', raw, k * 0x18)
            ents.append((v, p, typ, sz))
    ents.sort()
    return ents, total, nbucket


class Virt:
    """解压后的 RomFS 镜像虚拟读（按需解压块）。"""

    def __init__(self, rd, ents, total):
        self.rd = rd
        self.ents = ents
        self.total = total
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
        raw = self.rd.read(0x1894000 + p, sz)
        if typ == 0:
            data = raw[:n]
        else:
            data = lz4.block.decompress(raw, uncompressed_size=n)
        self.cache[i] = data
        return data

    def read(self, off, ln):
        out = bytearray()
        while ln > 0:
            i = self._locate(off)
            v = self.ents[i][0]
            end = self.ents[i + 1][0] if i + 1 < len(self.ents) else self.total
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

    def dir_info(off):
        par, nxt, cd, cf, h, nl = struct.unpack_from('<IIIIII', dm, off)
        name = dm[off + 0x18:off + 0x18 + nl].decode('utf-8', 'replace')
        return par, nxt, cd, cf, name

    def file_info(off):
        par, nxt, dofs, dsz, h, nl = struct.unpack_from('<IIQQII', fm, off)
        name = fm[off + 0x20:off + 0x20 + nl].decode('utf-8', 'replace')
        return par, nxt, dofs, dsz, name

    files = []

    def walk(dir_off, prefix):
        _, _, cd, cf, _ = dir_info(dir_off)
        o = cf
        while o != 0xFFFFFFFF and o < len(fm):
            par, nxt, dofs, dsz, nm = file_info(o)
            files.append((prefix + nm, fd_ofs + dofs, dsz))
            o = nxt
        o = cd
        while o != 0xFFFFFFFF and o < len(dm):
            par, nxt, c2, f2, nm = dir_info(o)
            walk(o, prefix + nm + '/')
            o = nxt

    walk(0, '')
    return files, (dh_ofs, dm_ofs, fh_ofs, fm_ofs, fd_ofs)


def main():
    nca = sys.argv[1]
    outdir = None
    for a in sys.argv[2:]:
        if a.startswith('--outdir='):
            outdir = a.split('=', 1)[1]
    rd = NcaReader(nca)
    ents, total, nb = parse_buckets(rd)
    print('[i] buckets=%d entries=%d uncompressed=%d' % (nb, len(ents), total))
    v = Virt(rd, ents, total)
    files, tables = parse_romfs(v)
    print('[i] romfs files=%d' % len(files))
    for name, off, sz in files[:40]:
        print('   %-80s %12d' % (name, sz))
    if len(files) > 40:
        print('   ... (%d more)' % (len(files) - 40))
    json.dump([{'name': n, 'offset': o, 'size': s} for n, o, s in files],
              open('_work_senjyushi/romfs_files.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('[i] wrote _work_senjyushi/romfs_files.json')


if __name__ == '__main__':
    main()
