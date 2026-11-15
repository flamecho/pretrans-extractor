# -*- coding: utf-8 -*-
"""VFS3 容器解包（日本一ソフトウェア / Rhapsody 系列，NS）

支持两种块长表布局（自动判别，见 `_load_chunks`）：

  A. **扁平数组**（[NS-JP]リトルプリンセス マール王国の人形姫２ 实测）
     chunk_ptr 处只有一个记录：`[u32 字节长][i32 块长 ×(字节长/4)]`，`4+字节长 == str_ptr-chunk_ptr`。
     数组按 **fid 升序** 一文件一段：
        stored（cs==us）→ 1 个 `0`
        压缩           → 1 个**元数据 u32**（stored 时为 0；实测与块长无关，可忽略）
                        ＋ ceil(us/131072) 个块长，∑块长 == cs
     合计 1107 + 141 + 2024 = 3272 项，逐项闭合（反例即失步）。
  B. **逐文件记录**（[NS-JP]マール王国の人形姫 实测）
     从固定偏移起 `[u32 字节长][i32 块长…]` 一条一文件，只对压缩文件存在，
     按 fid 升序用「∑==cs 且块数==ceil(us/131072)」严格匹配。

布局头（两作相同）：
  0x00 "VFS3" | 0x04 u32(=0x10) | 0x08 u32 目录数
  0x0C 目录表 n×28（crc,id,prev,next,nsub,unk,nfiles）
  u32 文件数 + 文件表 n×40（off u64, cs u64, us u64, crc, fid, folder, comp u16, dict i16）
  3×u64（chunk 表指针 / dict 指针 / 字符串表指针）  ← data_base = 此处
  字符串表：u32 n + n×(UTF-16LE NUL)，再 u32 m + m×同

压缩：**无帧头 zstd 块序列**（每块解压 131072 B，块间共享熵表）
      ⇒ 还原成 [magic][FHD=0x00][window=0x88][块头 L][块数据]… 再解。
"""
import struct, os, sys

import zstandard

MAGIC = b'VFS3'
BLOCK_OUT = 131072
LEGACY_CHUNK_OFF = 0x0C85C28C    # 布局 B 的首条记录偏移（マール王国の人形姫）


class VFS3:
    def __init__(self, path):
        self.path = path
        self.f = open(path, 'rb')
        f = self.f
        head = f.read(0x10)
        assert head[:4] == MAGIC, head[:4]
        self.ver = struct.unpack_from('<I', head, 4)[0]
        self.nfolder = struct.unpack_from('<I', head, 8)[0]
        f.seek(0x0C + self.nfolder * 28)
        self.nfile = struct.unpack('<I', f.read(4))[0]
        raw = f.read(self.nfile * 40)
        self.ents = []
        for i in range(self.nfile):
            e = i * 40
            off, cs, us = struct.unpack_from('<3Q', raw, e)
            crc, fid, folder = struct.unpack_from('<III', raw, e + 24)
            comp, dic = struct.unpack_from('<Hh', raw, e + 36)
            self.ents.append(dict(off=off, cs=cs, us=us, crc=crc, fid=fid,
                                  folder=folder, comp=comp, dict=dic))
        self.chunk_ptr, self.dict_ptr, self.str_ptr = struct.unpack('<3Q', f.read(24))
        self.data_base = f.tell()
        f.seek(self.str_ptr)

        def rstr():
            b = b''
            while True:
                c = f.read(2)
                if c == b'\x00\x00':
                    return b.decode('utf-16-le')
                b += c
        self.names = [rstr() for _ in range(struct.unpack('<I', f.read(4))[0])]
        self.folder_names = [rstr() for _ in range(struct.unpack('<I', f.read(4))[0])]
        self.layout = None
        self.chunks = self._load_chunks()
        self._d = zstandard.ZstdDecompressor()

    # ---------- 块长表 ----------
    @staticmethod
    def _nblk(us):
        return (us + BLOCK_OUT - 1) // BLOCK_OUT

    def _load_chunks(self):
        span = self.str_ptr - self.chunk_ptr if self.chunk_ptr else 0
        if self.chunk_ptr and span > 4:
            self.f.seek(self.chunk_ptr)
            L = struct.unpack('<I', self.f.read(4))[0]
            if 4 + L == span:
                self.layout = 'flat'
                blk = list(struct.unpack('<%di' % (L // 4), self.f.read(L)))
                return self._alloc_flat(blk)
        self.layout = 'records'
        return self._alloc_records()

    def _alloc_flat(self, blk):
        """fid 升序：stored 吃 1 个 0；压缩吃 1 个元数据 + ceil(us/B) 个块长。"""
        out = {}
        bi = 0
        for e in sorted(self.ents, key=lambda x: x['fid']):
            if e['cs'] == e['us']:
                assert blk[bi] == 0, ('stored 位非 0', e['fid'], blk[bi])
                bi += 1
                out[e['fid']] = None
                continue
            bi += 1                                   # 每文件一个元数据 u32（本作未用）
            n = self._nblk(e['us'])
            sizes = blk[bi:bi + n]
            bi += n
            assert sum(abs(v) for v in sizes) == e['cs'], \
                ('块长与 cs 不符', e['fid'], sum(abs(v) for v in sizes), e['cs'])
            out[e['fid']] = sizes
        assert bi == len(blk), ('块表未吃完', bi, len(blk))
        return out

    def _alloc_records(self):
        recs = []
        self.f.seek(LEGACY_CHUNK_OFF)
        while self.f.tell() < self.str_ptr:
            L = struct.unpack('<I', self.f.read(4))[0]
            recs.append(list(struct.unpack('<%di' % (L // 4), self.f.read(L))))
        out = {}
        ri = 0
        for fid in sorted(e['fid'] for e in self.ents):
            if ri >= len(recs):
                break
            e = next(x for x in self.ents if x['fid'] == fid)
            r = recs[ri]
            if abs(e['cs'] - sum(abs(v) for v in r)) == 0 and len(r) == self._nblk(e['us']):
                out[fid] = r
                ri += 1
        assert ri == len(recs), ('未匹配记录', len(recs) - ri)
        return out

    # ---------- 解压 ----------
    @staticmethod
    def _bh(L, last, raw=False):
        v = (L << 3) | ((0 if raw else 2) << 1) | (last & 1)
        return bytes([v & 0xff, (v >> 8) & 0xff, (v >> 16) & 0xff])

    def decompress(self, fid, blob, us):
        sizes = self.chunks.get(fid)
        if sizes is None:                                  # stored
            return blob
        assert sum(abs(x) for x in sizes) == len(blob), \
            (fid, sum(abs(x) for x in sizes), len(blob))
        frame = b'\x28\xb5\x2f\xfd\x00\x88'
        pos = 0
        for i, L in enumerate(sizes):
            last = 1 if i == len(sizes) - 1 else 0
            if L < 0:                                      # 未压缩块
                frame += self._bh(-L, last, raw=True) + blob[pos:pos - L]
                pos += -L
            else:
                frame += self._bh(L, last) + blob[pos:pos + L]
                pos += L
        return self._d.decompress(frame, max_output_size=us)

    def extract(self, outdir):
        os.makedirs(outdir, exist_ok=True)
        bad = []
        for e in self.ents:
            nm = self.names[e['fid']]
            self.f.seek(self.data_base + e['off'])
            blob = self.f.read(e['cs'])
            data = self.decompress(e['fid'], blob, e['us'])
            if len(data) != e['us']:
                bad.append((nm, len(data), e['us']))
            p = os.path.join(outdir, nm)
            open(p, 'wb').write(data)
        return len(self.ents), bad


if __name__ == '__main__':
    v = VFS3(sys.argv[1])
    print('files', v.nfile, 'folders', v.nfolder, 'layout', v.layout,
          'data_base', hex(v.data_base), 'chunks', len(v.chunks))
    n, bad = v.extract(sys.argv[2])
    print('extract', n, 'size_mismatch', len(bad))
    for b in bad[:5]:
        print('  WARN', b)
