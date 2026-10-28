#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ハンサムロンダリング 更新档（BKTR + LZ4 桶树）→ 最新 romfs 文件比对/提取。

结论（2026-10-26 实测，1.1.0 / 1.3.0 均通过）：
  · BKTR 的虚拟空间 = **section 起点为 0 的段内偏移**（不是 level5、也不是 romfs 起点）；
    romfs 头在 v = IVFC level5 起点（1.1.0 0x5D0000 / 1.3.0 0x5DC000）。
  · 数据块/表头一律用「普通段 CTR」：iv = (LE-u64(fsh+0x140) << 64) | ((sec_start + v) // 16)。
    （subsection 的 ctr 值本作不用；用了反而解成乱码。）
  · 段仍是**压缩 NCA**：压缩表在 v = level5 + fsh[+0x178].offset，桶树格式同本体。
  · 未 patch 区间 = base NCA 同段偏移的原字节（base 用 scripts/handsome_nca.py 的 Sec 读）。
  · 自洽：1.1.0 表 total 0x13935e5f0、1.3.0 0x13c061528（比本体 0x138e4a800 大 55 MB ⇒ 有新增内容）。

用法：
  python scripts/handsome_updraw.py <update.nsp> --list
  python scripts/handsome_updraw.py <update.nsp> --get <子串> --out <dir>
  python scripts/handsome_updraw.py <update.nsp> --diff          # 与本体 romfs 文件表比对
"""
import sys, os, struct
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lz4.block
from handsome_bktr import Upd
import handsome_nca as W

XCI = os.path.join(os.environ.get("VNTRANS_HOME", os.getcwd()), "src", "[NS-JP]ハンサムロンダリング -the mystic lover-", "[APP][010056B024B92000][1.0.0][JP][19.0.0].xci")
BASE_OFF = 0x1F033
BASE_L5 = 0x9dc000
BASE_KEY = '764ea2ad02a123cd860822303341bbb3'


class UpdRomfs:
    def __init__(self, nsp):
        os.environ['NCA_KEY'] = BASE_KEY
        self.bsec = W.Sec(XCI, base=BASE_OFF)
        self.u = Upd(nsp)
        lv = [struct.unpack_from('<QQQ', self.u.fsh, 0x18 + i * 0x18) for i in range(6)]
        self.l5 = lv[5][0]
        self.comp = struct.unpack_from('<QQ', self.u.fsh, 0x178)
        self.ents = None
        self.cache = {}
        self.total = 0
        self._read_table()

    # ---- 虚拟读（patch → 更新档物理；未 patch → base 同偏移）
    def vread(self, v, n):
        out = bytearray()
        rel = self.u.relocs
        while n > 0:
            cur = None
            nxt = None
            for e in rel:
                if e[0] <= v:
                    cur = e
                else:
                    nxt = e[0]
                    break
            if cur is None:
                break
            k = min(n, (nxt - v) if nxt else n)
            if cur[2]:
                out += self.u._plain(cur[1] + (v - cur[0]), k)
            else:
                # 未 patch 区间 = base 段内同偏移原字节（基准实测为「段内偏移」，非 level5 相对）
                out += self.bsec.read(1, cur[1] + (v - cur[0]), k)
            v += k
            n -= k
        return bytes(out)

    def _read_table(self):
        tbl = self.l5 + self.comp[0]
        h = self.vread(tbl, 0x10)
        nb = struct.unpack_from('<I', h, 4)[0]
        self.total = struct.unpack_from('<Q', h, 8)[0]
        ents = []
        for b in range(nb):
            bo = tbl + 0x4000 + b * 0x4000
            bh = self.vread(bo, 0x10)
            cnt = struct.unpack_from('<I', bh, 4)[0]
            if cnt > 0x4000:
                cnt = 0x4000
            raw = self.vread(bo + 0x10, cnt * 0x18)
            cnt = len(raw) // 0x18
            for k in range(cnt):
                ents.append(struct.unpack_from('<QQII', raw, k * 0x18))
        ents.sort()
        self.ents = ents
        print('[i] comp table buckets=%d entries=%d total=%#x (%.2f GB)' %
              (nb, len(ents), self.total, self.total / 2 ** 30))

    def block(self, i):
        if i in self.cache:
            return self.cache[i]
        v, p, typ, sz = self.ents[i]
        end = self.ents[i + 1][0] if i + 1 < len(self.ents) else self.total
        n = end - v
        if typ == 0:
            d = self.vread(self.l5 + p, n)
        else:
            raw = self.vread(self.l5 + p, sz)
            d = lz4.block.decompress(raw, uncompressed_size=n)
        if len(self.cache) > 256:
            self.cache.clear()
        self.cache[i] = d
        return d

    def _loc(self, off):
        lo, hi = 0, len(self.ents)
        while lo + 1 < hi:
            mid = (lo + hi) // 2
            if self.ents[mid][0] <= off:
                lo = mid
            else:
                hi = mid
        return lo

    def read(self, off, ln):
        out = bytearray()
        while ln > 0:
            i = self._loc(off)
            v = self.ents[i][0]
            b = self.block(i)
            s = off - v
            take = min(len(b) - s, ln)
            if take <= 0:
                raise RuntimeError('bad block at %#x' % off)
            out += b[s:s + take]
            off += take
            ln -= take
        return bytes(out)

    def files(self):
        hdr = self.read(0, 0x50)
        (hs, dh_ofs, dh_sz, dm_ofs, dm_sz, fh_ofs, fh_sz, fm_ofs, fm_sz, fd_ofs) = struct.unpack('<10Q', hdr)
        dm = self.read(dm_ofs, dm_sz)
        fm = self.read(fm_ofs, fm_sz)

        def dir_info(off):
            par, nxt, cd, cf, h, nl = struct.unpack_from('<IIIIII', dm, off)
            return nxt, cd, cf, dm[off + 0x18:off + 0x18 + nl].decode('utf-8', 'replace')

        def file_info(off):
            par, nxt, dofs, dsz, h, nl = struct.unpack_from('<IIQQII', fm, off)
            return nxt, dofs, dsz, fm[off + 0x20:off + 0x20 + nl].decode('utf-8', 'replace')

        out = []

        def walk(doff, prefix):
            _, cd, cf, _ = dir_info(doff)
            o = cf
            while o != 0xFFFFFFFF and o < len(fm):
                nxt, dofs, dsz, nm = file_info(o)
                out.append((prefix + nm, fd_ofs + dofs, dsz))
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
        return out


def main():
    nsp = sys.argv[1]
    args = sys.argv[2:]
    r = UpdRomfs(nsp)
    files = r.files()
    print('[i] update romfs files=%d' % len(files))
    if '--diff' in args:
        import json
        b = json.load(open('_w_w4_handsome/romfs_files.json', encoding='utf-8'))
        bm = {f['name']: (f['offset'], f['size']) for f in b}
        um = {n: (o, s) for n, o, s in files}
        add = sorted(set(um) - set(bm))
        rem = sorted(set(bm) - set(um))
        chg = sorted(n for n in set(um) & set(bm) if um[n][1] != bm[n][1])
        print('added %d removed %d size-changed %d' % (len(add), len(rem), len(chg)))
        for n in add[:20]:
            print('  + %s (%d)' % (n, um[n][1]))
        for n in rem[:20]:
            print('  - %s' % n)
        for n in chg[:20]:
            print('  * %s %d -> %d' % (n, bm[n][1], um[n][1]))
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
                        w.write(r.read(o + k, min(1 << 22, s - k)))
                print('   -> %s (%d)' % (p, s))
        return
    for n, o, s in files:
        print('%12d %s' % (s, n))


if __name__ == '__main__':
    main()
