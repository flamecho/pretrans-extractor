#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""レッドベルの慟哭 —— 压缩 NCA(LZ4 bucket-tree) → RomFS 直读。

参数由 NCA 头/FS 头实测（见报告）：
  sec1 @0x1c000 size 0x1a7f44000 | ctr_hi 0x0000000200000000 | key 618eeafbfced69ea5667ffa85ab851ec
  IVFC level5(数据层) @0xE30000 | CompressionInfo: TableOffset 0x1a6e44000, TableSize 0x2d0000
用法:
  python scripts/redbell_romfs.py --list
  python scripts/redbell_romfs.py --get <outdir> [名子串...]
"""
import struct, sys, os
import lz4.block
from Crypto.Cipher import AES
from Crypto.Util import Counter
import UnityPy  # noqa

NSP = '_w_W1_redbell/The Red Bells Lament[01006660233C6000][1.0.0][0][19.0.1].nsp'
NCA_BASE = 0x1944
SEC1_OFF = 0x1c000
SEC1_SIZE = 0x1a7f44000
CTR_HI = bytes.fromhex('0000000200000000')
KEY = bytes.fromhex('618eeafbfced69ea5667ffa85ab851ec')
LEVEL5 = 0xE30000
TBL_OFF = 0x1a6e44000


class Rd:
    def __init__(self):
        self.f = open(NSP, 'rb')

    def read(self, pos, ln):
        a = SEC1_OFF + pos
        ctr = CTR_HI + (a // 16).to_bytes(8, 'big')
        c = AES.new(KEY, AES.MODE_CTR,
                    counter=Counter.new(128, initial_value=int.from_bytes(ctr, 'big')))
        self.f.seek(NCA_BASE + a)
        raw = self.f.read(ln + 16)
        return c.decrypt(raw)[:ln]


def parse_buckets(rd):
    T = LEVEL5 + TBL_OFF
    hdr = rd.read(T, 0x10)
    nbucket = struct.unpack_from('<I', hdr, 4)[0]
    total = struct.unpack_from('<Q', hdr, 8)[0]
    ents = []
    for b in range(nbucket):
        b0 = T + 0x4000 + b * 0x4000
        bh = rd.read(b0, 0x10)
        cnt = struct.unpack_from('<I', bh, 4)[0]
        if not (0 < cnt < 200000):
            continue
        raw = rd.read(b0 + 0x10, cnt * 0x18)
        for k in range(cnt):
            v, p, typ, sz = struct.unpack_from('<QQII', raw, k * 0x18)
            ents.append((v, p, typ, sz))
    ents.sort()
    return ents, total, nbucket


class Virt:
    def __init__(self, rd, ents, total):
        self.rd, self.ents, self.total, self.cache = rd, ents, total, {}

    def _loc(self, off):
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
        raw = self.rd.read(LEVEL5 + p, n if typ == 0 else sz)
        data = raw[:n] if typ == 0 else lz4.block.decompress(raw, uncompressed_size=n)
        self.cache[i] = data
        return data

    def read(self, off, ln):
        out = bytearray()
        while ln > 0:
            i = self._loc(off)
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
    hs, dh_o, dh_s, dm_o, dm_s, fh_o, fh_s, fm_o, fm_s, fd_o = struct.unpack('<10Q', v.read(0, 0x50))
    dm = v.read(dm_o, dm_s)
    fm = v.read(fm_o, fm_s)
    files = []

    def dinfo(o):
        return struct.unpack_from('<IIIIII', dm, o)

    def finfo(o):
        return struct.unpack_from('<IIQQII', fm, o)

    def walk(o, prefix):
        _, _, cd, cf, _, _ = dinfo(o)
        p = cf
        while p != 0xFFFFFFFF and p + 0x20 <= len(fm):
            par, nxt, dofs, dsz, h, nl = finfo(p)
            files.append((prefix + fm[p + 0x20:p + 0x20 + nl].decode('utf-8', 'replace'), fd_o + dofs, dsz))
            p = nxt
        p = cd
        while p != 0xFFFFFFFF and p + 0x18 <= len(dm):
            par, nxt, c2, f2, h, nl = dinfo(p)
            walk(p, prefix + dm[p + 0x18:p + 0x18 + nl].decode('utf-8', 'replace') + '/')
            p = nxt

    walk(0, '')
    return files


def main():
    rd = Rd()
    ents, total, nb = parse_buckets(rd)
    print('[i] buckets=%d entries=%d total=%d' % (nb, len(ents), total))
    v = Virt(rd, ents, total)
    files = parse_romfs(v)
    print('[i] romfs files=%d' % len(files))
    mode = sys.argv[1] if len(sys.argv) > 1 else '--list'
    if mode == '--list':
        for n, o, s in sorted(files, key=lambda x: -x[2])[:40]:
            print('%12d  %s' % (s, n))
        return
    outdir = sys.argv[2]
    wants = sys.argv[3:]
    os.makedirs(outdir, exist_ok=True)
    for n, o, s in files:
        if wants and not any(w.lower() in n.lower() for w in wants):
            continue
        dst = os.path.join(outdir, os.path.basename(n))
        with open(dst, 'wb') as g:
            pos = 0
            while pos < s:
                k = min(1 << 24, s - pos)
                g.write(v.read(o + pos, k))
                pos += k
        print('[+] %s -> %s (%d)' % (n, dst, s))


if __name__ == '__main__':
    main()
