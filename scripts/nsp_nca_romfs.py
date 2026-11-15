"""ワンド オブ フォーチュン Ｒ２（Switch）—— NSP → Program NCA → RomFS 枚举／导出

本作实测要点（2026-10-28）：
  * NCA 头 AES-XTS：k1/k2 = header_key[0:16]/[16:32]，tweak 为「扇区号大端 + 块内 rev(α(rev(T)))」
  * titlekey = AES_ECB_dec(titlekek_<keygen-1>, tik[0x180:0x190])      ★ 索引是 keygen-1
  * 段 AES-CTR：ctr_high8 = fs_header[0x741:0x749]，ctr_low8 = NCA 内绝对偏移/16
  * IVFC level 表：fs_header+0x18 起，stride 0x18 = (u64 offset, u64 size, u64 block_log2)，
    最后一个非空 level 即 data layer

用法：
  python wfr2_extract.py <nsp> --list
  python wfr2_extract.py <nsp> --out <dir> [--filter CPK]
"""
import argparse
import os
import struct

from Crypto.Cipher import AES
from Crypto.Util import Counter

KEYS = r'<本地路径>'
MASK = (1 << 128) - 1
SECTOR = 0x200


def load_keys(path=KEYS):
    d = {}
    for line in open(path, encoding='utf-8', errors='ignore'):
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            d[k.strip()] = v.strip()
    return d


def alpha(T):
    c = T >> 127
    T = (T << 1) & MASK
    if c:
        T ^= 0x87
    return T


def xts_decrypt(k1, k2, base, data):
    a1 = AES.new(k1, AES.MODE_ECB)
    a2 = AES.new(k2, AES.MODE_ECB)

    def rev(x):
        return int.from_bytes(x.to_bytes(16, 'big'), 'little')

    out = bytearray()
    for s in range(0, len(data), SECTOR):
        chunk = data[s:s + SECTOR]
        T = int.from_bytes(a2.encrypt(((base + s) // SECTOR).to_bytes(16, 'big')), 'big')
        for b in range(0, len(chunk) - len(chunk) % 16, 16):
            blk = chunk[b:b + 16]
            tb = T.to_bytes(16, 'big')
            p = a1.decrypt(bytes(x ^ y for x, y in zip(blk, tb)))
            out += bytes(m ^ n for m, n in zip(p, tb))
            T = rev(alpha(rev(T)))
    return bytes(out)


class Nsp:
    def __init__(self, path):
        self.path = path
        self.f = open(path, 'rb')
        d = self.f.read(0x40)
        assert d[:4] == b'PFS0', 'not PFS0: %r' % d[:4]
        self.nf, self.strtab = struct.unpack_from('<II', d, 4)
        self.hdr_end = 0x10 + self.nf * 0x18
        self.f.seek(0x10)
        raw_entries = [struct.unpack('<QQII', self.f.read(0x18)) for _ in range(self.nf)]
        table = self.f.read(self.strtab)
        data0 = self.hdr_end + self.strtab

        def nm(so):
            e = table.find(b'\0', so)
            return table[so:e].decode('utf-8', 'replace')

        self.entries = [(nm(so), data0 + off, sz) for off, sz, so, _ in raw_entries]

    def read(self, off, n):
        self.f.seek(off)
        return self.f.read(n)

    def tik_for(self, rights_id):
        for name, off, sz in self.entries:
            if name.endswith('.tik'):
                t = self.read(off, sz)
                if t[0x2A0:0x2B0] == rights_id:
                    return t
        return None


class Romfs:
    def __init__(self, nsp, nca_off, hdr, keys):
        self.nsp = nsp
        self.nca_off = nca_off
        self.keygen = hdr[0x206] if False else struct.unpack_from('<I', hdr, 0x220)[0] & 0xFF
        self.rights = hdr[0x230:0x240]
        # 段密钥：有 Rights ID ⇒ titlekey（titlekek 索引 = keygen-1）；
        #           Rights ID 全 0 ⇒ key_area 四槽（key_area_key_application_<keygen-1> 解出）
        if self.rights != b'\x00' * 16:
            tik = nsp.tik_for(self.rights)
            assert tik, '找不到匹配的 tik（rights %s）' % self.rights.hex()
            tkek = bytes.fromhex(keys['titlekek_%02x' % (self.keygen - 1)])
            self.titlekey = AES.new(tkek, AES.MODE_ECB).decrypt(tik[0x180:0x190])
            self.key_candidates = [self.titlekey]
        else:
            kaek = AES.new(bytes.fromhex(keys['key_area_key_application_%02x' % (self.keygen - 1)]), AES.MODE_ECB)
            self.key_candidates = [kaek.decrypt(hdr[0x300 + i * 16:0x310 + i * 16]) for i in range(4)]
            self.titlekey = None
        # 找 RomFS 段（fs header magic == IVFC 的那一段）
        self.sec_off = self.sec_end = None
        for i in range(4):
            fsh = 0x400 + i * 0x200
            if hdr[fsh + 0x08:fsh + 0x0C] == b'IVFC':
                ms, me = struct.unpack_from('<II', hdr, 0x240 + i * 0x10)
                self.sec_off, self.sec_end = ms * 0x200, me * 0x200
                self.ctr_high = int.from_bytes(hdr[fsh + 0x141:fsh + 0x149], 'big')
                nlev = struct.unpack_from('<I', hdr, fsh + 0x14)[0]
                data_off = data_size = 0
                for k in range(nlev):
                    o, s = struct.unpack_from('<QQ', hdr, fsh + 0x18 + k * 0x18)
                    if s:
                        data_off, data_size = o, s
                self.ivfc_data_off, self.ivfc_data_size = data_off, data_size
                break
        assert self.sec_off is not None, '没找到 IVFC 段'
        self.romfs_abs = nca_off + self.sec_off + self.ivfc_data_off
        # 无 titlekey 时：用 romfs 头 header_size==0x50 挑出正确的 key_area 槽
        if self.titlekey is None:
            for i, k in enumerate(self.key_candidates):
                self.titlekey = k
                h = self._raw_dec(0, 8)
                if struct.unpack_from('<Q', h, 0)[0] == 0x50:
                    self.key_slot = i
                    break
            else:
                raise AssertionError('key_area 四个槽都解不出 romfs 头')

    def dec(self, off, n):
        return self._raw_dec(off, n)

    def _raw_dec(self, off, n):
        # ★ RomFS 元数据只保证 4 字节对齐，必须按 16 字节块取整后切片。
        # ⚠ 块的基准是 **NCA 起点**（容器内 NCA 偏移可能不是 16 的倍数，如 0xC146FF），
        #   所以对齐要相对 nca_off 做，不能直接对文件绝对偏移取模。
        abs_off = self.romfs_abs + off
        rel = abs_off - self.nca_off
        blk = rel - (rel % 16)
        aligned = self.nca_off + blk
        pad = abs_off - aligned
        want = pad + n
        want += (-want) % 16
        self.nsp.f.seek(aligned)
        raw = self.nsp.f.read(want)
        # CTR 的低 8 字节用的是「NCA 内绝对偏移/16」，不是容器内偏移
        iv = (self.ctr_high << 64) | (blk // 16)
        c = AES.new(self.titlekey, AES.MODE_CTR, counter=Counter.new(128, initial_value=iv))
        out = c.decrypt(raw)
        return out[pad:pad + n]

    def header(self):
        v = struct.unpack('<10Q', self.dec(0, 0x50))
        keys = ['header_size', 'dir_hash_off', 'dir_hash_size', 'dir_meta_off', 'dir_meta_size',
                'file_hash_off', 'file_hash_size', 'file_meta_off', 'file_meta_size', 'data_off']
        return dict(zip(keys, v))

    def file_bytes(self, off, size):
        """file 表里的 offset 是相对 romfs header 的 data_off，不是相对镜像起点。"""
        return self.dec(self.header()['data_off'] + off, size)

    def entries(self):
        h = self.header()
        meta = self.dec(h['dir_meta_off'], h['dir_meta_size'])
        fmeta = self.dec(h['file_meta_off'], h['file_meta_size'])
        self._meta, self._fmeta = meta, fmeta
        yield from self._walk(0, '', first=True)

    def orphans(self):
        """★ 目录树没覆盖到的 file 表条目。

        2026-10-28 [NS]ビルシャナ戦姫 本体：目录遍历只给出 120 项，而 file 表有 158 项，
        漏掉的正是 `common/script.memfs` / `script.membody` / `app_info.rson` /
        `bir_nam_kana_kanji_dict.rson`（2.36 MB）——据此曾误判「源里没有剧本」。
        ⇒ 列完目录**必须**跑这个，差额非 0 就按 file 表补全。
        """
        seen = {(o, s) for t, _p, o, s in self.entries() if t == 'file'}
        fmeta = self._fmeta
        out, i = [], 0
        while i + 0x20 <= len(fmeta):
            _parent, _nxt, doff, dsize = struct.unpack_from('<IIQQ', fmeta, i)
            nl = struct.unpack_from('<I', fmeta, i + 0x1C)[0]
            if nl > 512 or i + 0x20 + nl > len(fmeta):
                break
            nm = fmeta[i + 0x20:i + 0x20 + nl].decode('utf-8', 'replace')
            if (doff, dsize) not in seen:
                out.append((nm, doff, dsize))
            i += 0x20 + nl + ((4 - nl % 4) % 4)   # ★ 别漏了 nl 本身
        return out

    def _walk(self, off, prefix, first=False):
        meta, fmeta = self._meta, self._fmeta
        NULL = 0xFFFFFFFF
        while first or off not in (0, NULL):
            first = False
            parent, nxt, child, fileno, _h = struct.unpack_from('<IIIII', meta, off)
            nl = struct.unpack_from('<I', meta, off + 0x14)[0]
            name = meta[off + 0x18:off + 0x18 + nl].decode('utf-8', 'replace')
            path = (prefix + '/' + name) if name else (prefix or '/')
            if name:
                yield ('dir', path, 0, 0)
            if child not in (0, NULL):
                yield from self._walk(child, path)
            fidx = fileno
            # ★★ 文件链的**索引 0 是合法条目**（根目录第一项就是 0），只有 0xFFFFFFFF 才是结束符。
            #   曾写成 `not in (0, NULL)` ⇒ 根目录 4 个文件全被跳过（ビルシャナ本体误判「源里没有剧本」）。
            while fidx != NULL:
                _p2, n2, doff, dsize = struct.unpack_from('<IIQQ', fmeta, fidx)
                nl2 = struct.unpack_from('<I', fmeta, fidx + 0x1C)[0]
                fname = fmeta[fidx + 0x20:fidx + 0x20 + nl2].decode('utf-8', 'replace')
                yield ('file', path + '/' + fname, doff, dsize)
                fidx = n2
            off = nxt


def open_romfs(nsp_path, keys=None):
    keys = keys or load_keys()
    nsp = Nsp(nsp_path)
    hk = bytes.fromhex(keys['header_key'])
    prog = max([e for e in nsp.entries if e[0].endswith('.nca')], key=lambda e: e[2])
    hdr = xts_decrypt(hk[:16], hk[16:], 0, nsp.read(prog[1], 0x1200))
    assert hdr[0x200:0x204] == b'NCA3', 'NCA 头解密失败'
    return nsp, prog, hdr, Romfs(nsp, prog[1], hdr, keys)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('nsp')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--out')
    ap.add_argument('--filter', default='')
    a = ap.parse_args()
    nsp, prog, hdr, rf = open_romfs(a.nsp)
    print('NSP 成员:')
    for name, off, sz in nsp.entries:
        print(f'  {name:44s} {sz:#012x}')
    print(f'Program NCA: {prog[0]} size={prog[2]:#x} keygen={rf.keygen}')
    print(f'titlekey={rf.titlekey.hex()} sec1={rf.sec_off:#x}/{rf.sec_end:#x} '
          f'romfs@{rf.romfs_abs:#x} size={rf.ivfc_data_size:#x}')
    print('romfs header:', {k: hex(v) for k, v in rf.header().items()})
    rows = list(rf.entries())
    files = [r for r in rows if r[0] == 'file']
    print(f'条目: 目录 {len(rows) - len(files)} / 文件 {len(files)}')
    orph = rf.orphans()
    if orph:
        print(f'⚠ 孤儿条目 {len(orph)} 项（目录树未覆盖，按 file 表补）：')
        for nm, o, sz in orph[:20]:
            print(f'    {sz:>12} off={o:#x} {nm}')
    if a.list:
        for t, p, o, s in rows:
            if a.filter.lower() in p.lower():
                print(f'  {"D" if t=="dir" else "F"} {s:>12} {p}')


if __name__ == '__main__':
    main()
