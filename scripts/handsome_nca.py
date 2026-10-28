#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ハンサムロンダリング -the mystic lover- (NS) 压缩 NCA（LZ4 桶树）解包。

复制自 scripts/neon_nca.py（原文件不动），仅改：① 可直接读 XCI 内的 NCA（--base 绝对偏移）；
② 默认 keyset = _sw/merged.keys（keygen 21 ⇒ prod_fixed 不够）；③ 输出目录改 _w_w4_handsome。

链路: XCI@0x1F033 -> NCA -> section1(RomFS, AesCtr) -> IVFC level6 -> 压缩表 -> LZ4 -> RomFS

★ 本作校准结论（2026-10-26）：
  1) XCI root HFS0 @0xF000，条目布局是 {offset,size,nameoff}（非标准）⇒ secure HFS0 @0x17033，
     数据区实际起点 0x1F033（条目 offset 相对 0x171DC，中间 0x7E57 零填充）。
  2) NCA = c72855d4…，3,128,639,488 B，keygen 21 ⇒ key_area 槽 2 用
     key_area_key_application_14 (AES-ECB-dec) 解出内容密钥；槽 0/1/3 解出全 0。
     自证：解出的 romfs 段 level5 首 = `50 00 00 00 …`（header_size=0x50）。
  3) CTR 初值 = **0x02 前缀** | BE64(段内绝对偏移/16)；段表 @0x240 是 {start,end}（×0x200）。
  4) FS 头在 0x400+sid*0x200，IVFC 魔数在 +0x8、level 表 @+0x18、CompressionInfo @+0x178
     = {u64 TableOffset（相对 level5 起点）, u64 TableSize}；本作
     TableOffset 0xB7014000 + TableSize 0x1E0000 == level5 尺寸 0xB71F4000（自洽）。
  5) 桶树: 表头 {u32 pad, u32 bucket_count, u64 total}；桶自表+0x4000 起每 0x4000:
     {u32 idx, u32 count, u64 end}；条目 @桶+0x10，0x18/条 {u64 v, u64 p, u32 type, u32 size}；
     块 0x10000，type 0=raw / 3=LZ4（必须按 comp_size 精确截，physical 是 0x10 对齐的）。

用法: NCA_KEY=<32hex> python scripts/handsome_nca.py <xci|nca> --base 0x1F033 --list
      NCA_KEY=<32hex> python scripts/handsome_nca.py <xci|nca> --base 0x1F033 --extract <outdir> [--filter <substr>]
"""
import sys, os, struct, json
import lz4.block
from Crypto.Cipher import AES
from Crypto.Util import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import switch_nca as SN

BLOCK = 0x10000


class Sec:
    def __init__(self, nca, base=0, keyset='_sw/merged.keys'):
        self.f = open(nca, 'rb')
        self.base = base
        keys = SN.load_keys(keyset)
        self.f.seek(base)
        hdr = SN.xts_decrypt(bytes.fromhex(keys['header_key'][:32]),
                             bytes.fromhex(keys['header_key'][32:64]), 0, self.f.read(0x1200))
        assert hdr[0x200:0x204] == b'NCA3'
        # ★ 本作：Standard crypto（rights_id 全 0）⇒ 内容密钥由 key_area 槽解出，经 NCA_KEY 传入
        self.key = bytes.fromhex(os.environ.get('NCA_KEY', '00' * 16))
        self.hdr = hdr
        self.secs = [(int.from_bytes(hdr[0x240 + i * 0x10:0x244 + i * 0x10], 'little') * 0x200,
                      int.from_bytes(hdr[0x244 + i * 0x10:0x248 + i * 0x10], 'little') * 0x200)
                     for i in range(4)]
        self.levels = {}
        for sid in range(4):
            base = 0x400 + sid * 0x200
            if hdr[base + 8:base + 12] != b'IVFC':
                continue
            lv = [struct.unpack_from('<QQI', hdr, base + 0x18 + i * 0x18) for i in range(6)]
            comp = struct.unpack_from('<QQ', hdr, base + 0x178)
            self.levels[sid] = (lv, comp)

    def read(self, sec, off, n):
        st = self.secs[sec][0]
        c = AES.new(self.key, AES.MODE_CTR,
                    counter=Counter.new(128, initial_value=(2 << 96) | ((st + off) // 16)))
        self.f.seek(self.base + st + off)
        return c.decrypt(self.f.read(n))


class BucketRomfs:
    def __init__(self, sec, sid):
        self.sec = sec
        lv, comp = sec.levels[sid]
        self.data_off = lv[5][0]            # level6 物理起点（段内）
        self.data_size = lv[5][1]
        self.tbl = self.data_off + comp[0]  # 表 = data + TableOffset
        h = sec.read(sid, self.tbl, 0x10)
        self.nbucket = struct.unpack_from('<I', h, 4)[0]
        self.total = struct.unpack_from('<Q', h, 8)[0]
        self.ents = []
        for b in range(self.nbucket):
            bh = sec.read(sid, self.tbl + 0x4000 + b * 0x4000, 0x10)
            cnt = struct.unpack_from('<I', bh, 4)[0]
            raw = sec.read(sid, self.tbl + 0x4000 + b * 0x4000 + 0x10, cnt * 0x18)
            for k in range(cnt):
                v, p, typ, sz = struct.unpack_from('<QQII', raw, k * 0x18)
                self.ents.append((v, p, typ, sz))
        self.ents.sort()
        self.cache = {}

    def block(self, i):
        if i in self.cache:
            return self.cache[i]
        v, p, typ, sz = self.ents[i]
        end = self.ents[i + 1][0] if i + 1 < len(self.ents) else self.total
        n = end - v          # 块长可变（64K/128K/…），必须按相邻 v 差取
        if typ == 0:
            data = self.sec.read(self.sid, self.data_off + p, n)
        else:
            raw = self.sec.read(self.sid, self.data_off + p, sz)
            data = lz4.block.decompress(raw, uncompressed_size=n)
        if len(self.cache) > 512:
            self.cache.clear()
        self.cache[i] = data
        return data

    def read(self, off, ln):
        out = bytearray()
        while ln > 0:
            i = self._locate(off)
            v = self.ents[i][0]
            b = self.block(i)
            s = off - v
            take = min(len(b) - s, ln)
            if take <= 0:
                raise RuntimeError('block %d empty at off %d (v=%d len=%d)' % (i, off, v, len(b)))
            out += b[s:s + take]
            off += take
            ln -= take
        return bytes(out)

    def _locate(self, off):
        lo, hi = 0, len(self.ents)
        while lo + 1 < hi:
            mid = (lo + hi) // 2
            if self.ents[mid][0] <= off:
                lo = mid
            else:
                hi = mid
        return lo


def parse_romfs(v):
    hdr = v.read(0, 0x50)
    hs, dh_ofs, dh_sz, dm_ofs, dm_sz, fh_ofs, fh_sz, fm_ofs, fm_sz, fd_ofs = struct.unpack('<10Q', hdr)
    dm = v.read(dm_ofs, dm_sz)
    fm = v.read(fm_ofs, fm_sz)

    def dir_info(off):
        par, nxt, cd, cf, h, nl = struct.unpack_from('<IIIIII', dm, off)
        return par, nxt, cd, cf, dm[off + 0x18:off + 0x18 + nl].decode('utf-8', 'replace')

    def file_info(off):
        par, nxt, dofs, dsz, h, nl = struct.unpack_from('<IIQQII', fm, off)
        return par, nxt, dofs, dsz, fm[off + 0x20:off + 0x20 + nl].decode('utf-8', 'replace')

    files = []

    def walk(doff, prefix):
        _, _, cd, cf, _ = dir_info(doff)
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
    return files, fd_ofs


def main():
    nca = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else '--list'
    outdir = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else None
    filt = None
    base = 0
    for a in sys.argv[2:]:
        if a.startswith('--filter='):
            filt = a.split('=', 1)[1]
        if a.startswith('--base='):
            base = int(a.split('=', 1)[1], 0)
    sec = Sec(nca, base=base)
    print('[i] keygen=%d key=%s' % (max(sec.hdr[0x206], sec.hdr[0x220]), sec.key.hex()))
    print('[i] sections', [(hex(a), hex(b)) for a, b in sec.secs])
    print('[i] IVFC secs', sorted(sec.levels))
    b = BucketRomfs(sec, 1)
    b.sid = 1
    print('[i] buckets=%d entries=%d total=%d (%.2f GB)' % (b.nbucket, len(b.ents), b.total, b.total / 2 ** 30))
    files, fd = parse_romfs(b)
    print('[i] romfs files=%d data_base=0x%x' % (len(files), fd))
    os.makedirs('_w_w4_handsome', exist_ok=True)
    json.dump([{'name': n, 'offset': o, 'size': s} for n, o, s in files],
              open('_w_w4_handsome/romfs_files.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if mode == '--list':
        for n, o, s in files:
            print('   %-70s %10d' % (n, s))
        return
    sel = [x for x in files if filt is None or filt.lower() in x[0].lower()]
    for n, o, s in sel:
        print('   -> %s (%d)' % (n, s), flush=True)
        p = os.path.join(outdir, n.replace('/', os.sep))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'wb') as w:
            step = 0x400000
            for k in range(0, s, step):
                w.write(b.read(o + k, min(step, s - k)))
    print('[i] extracted %d files -> %s' % (len(sel), outdir))


if __name__ == '__main__':
    main()
