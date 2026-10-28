#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用：NSP/PFS0（或裸 NCA）内**未压缩** RomFS 的就地列出/提取。

适用 even if TEMPEST 連なるときの暁（keygen 16 / Titlekey crypto / IVFC 无 CompressionInfo）。

链路：PFS0 → 最大 NCA → XTS 解头 → 内容密钥（rights_id 非 0 ⇒ titlekey = AES-ECB-dec(titlekek[gen-1], tik[0x180:0x190])）
      → 段 CTR（hi = LE-u64(fs头+0x140)，low = 段内绝对偏移/16）→ romfs 头 → 目录表 → 按需读文件。

用法:
  python scripts/nsp_plainromfs.py <nsp|nca> --list [--filter=子串]
  python scripts/nsp_plainromfs.py <nsp|nca> --get 子串 --out <dir>
"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import switch_nca as SN
from Crypto.Cipher import AES
from Crypto.Util import Counter


def pfs0(path):
    f = open(path, 'rb')
    h = f.read(0x10)
    if h[:4] != b'PFS0':
        f.close()
        return []
    n, strsz = struct.unpack_from('<II', h, 4)
    ents = []
    for _ in range(n):
        off, size, so, _ = struct.unpack('<QQII', f.read(0x18))
        ents.append([off, size, so])
    st = f.read(strsz)
    f.close()
    data = 0x10 + n * 0x18 + strsz
    return [(st[e[2]:st.index(b'\0', e[2])].decode('utf-8', 'replace'), data + e[0], e[1]) for e in ents]


class Nca:
    def __init__(self, path, off, keys, tik=None):
        self.f = open(path, 'rb')
        self.off = off
        self.keys = keys
        self.f.seek(off)
        hdr = SN.xts_decrypt(bytes.fromhex(keys['header_key'][:32]), bytes.fromhex(keys['header_key'][32:64]),
                             0, self.f.read(0x4000))
        assert hdr[0x200:0x204] == b'NCA3', hdr[0x200:0x204]
        self.hdr = hdr
        self.gen = hdr[0x220]
        self.rights = hdr[0x230:0x240]
        self.secs = []
        for i in range(4):
            e = hdr[0x240 + i * 0x10:0x250 + i * 0x10]
            self.secs.append((int.from_bytes(e[0:4], 'little') * 0x200, int.from_bytes(e[4:8], 'little') * 0x200))
        self.sid = next(i for i in range(4) if hdr[0x400 + i * 0x200 + 8:0x400 + i * 0x200 + 12] == b'IVFC')
        self.fsh = hdr[0x400 + self.sid * 0x200:0x600 + self.sid * 0x200]
        self.hi = int.from_bytes(self.fsh[0x140:0x148], 'little')
        self.key = self._key(tik)

    def _key(self, tik):
        if any(self.rights):
            blk = tik[0x180:0x190]
            for rev in (self.gen - 1, self.gen):
                k = self.keys.get('titlekek_%02x' % rev)
                if k:
                    tk = AES.new(bytes.fromhex(k), AES.MODE_ECB).decrypt(blk)
                    print('[i] titlekey (titlekek_%02x) = %s' % (rev, tk.hex()))
                    return tk
            raise SystemExit('缺 titlekek')
        kak = self.keys.get('key_area_key_application_%02x' % max(self.hdr[0x207], self.gen - 1))
        for i in range(4):
            blk = self.hdr[0x300 + i * 16:0x310 + i * 16]
            if any(blk):
                return AES.new(bytes.fromhex(kak), AES.MODE_ECB).decrypt(blk)
        raise SystemExit('key_area 全 0 且无 rights_id')

    def read(self, addr, n):
        # addr = 段内偏移（相对 section1 起点）
        st = self.secs[self.sid][0]
        rel = addr & ~0xF
        pad = addr - rel
        iv = (self.hi << 64) | ((st + rel) >> 4)
        c = AES.new(self.key, AES.MODE_CTR, counter=Counter.new(128, initial_value=iv))
        self.f.seek(self.off + st + rel)
        return c.decrypt(self.f.read(((n + pad + 15) // 16) * 16))[pad:pad + n]


def parse_romfs(v):
    (hs, dh_ofs, dh_sz, dm_ofs, dm_sz, fh_ofs, fh_sz, fm_ofs, fm_sz, fd_ofs) = struct.unpack('<10Q', v.read(0, 0x50))
    dm = v.read(dm_ofs, dm_sz)
    fm = v.read(fm_ofs, fm_sz)

    def di(off):
        par, nxt, cd, cf, h, nl = struct.unpack_from('<IIIIII', dm, off)
        return nxt, cd, cf, dm[off + 0x18:off + 0x18 + nl].decode('utf-8', 'replace')

    def fi(off):
        par, nxt, dofs, dsz, h, nl = struct.unpack_from('<IIQQII', fm, off)
        return nxt, dofs, dsz, fm[off + 0x20:off + 0x20 + nl].decode('utf-8', 'replace')

    out = []

    def walk(doff, prefix):
        _, cd, cf, _ = di(doff)
        o = cf
        while o != 0xFFFFFFFF and o < len(fm):
            nxt, dofs, dsz, nm = fi(o)
            out.append((prefix + nm, fd_ofs + dofs, dsz))
            if nxt == o:
                break
            o = nxt
        o = cd
        while o != 0xFFFFFFFF and o < len(dm):
            nxt, _, _, nm = di(o)
            walk(o, prefix + nm + '/')
            if nxt == o:
                break
            o = nxt

    walk(0, '')
    return out, fd_ofs


class SecView:
    def __init__(self, nca, base):
        self.nca, self.base = nca, base

    def read(self, off, n):
        return self.nca.read(self.base + off, n)


def open_nsp(path):
    keys = SN.load_keys('_sw/merged.keys')
    ents = pfs0(path)
    if ents:
        tik = next((x for x in ents if x[0].endswith('.tik')), None)
        tib = None
        if tik:
            with open(path, 'rb') as f:
                f.seek(tik[1]); tib = f.read(tik[2])
            print('[i] tik %s rights=%s' % (tik[0], tib[0x2A0:0x2B0].hex()))
        nca = max((x for x in ents if x[0].endswith('.nca') and 'cnmt' not in x[0]), key=lambda x: x[2])
    else:
        tib = None
        nca = (os.path.basename(path), 0, os.path.getsize(path))
    print('[i] NCA %s %d B @%#x' % (nca[0], nca[2], nca[1]))
    n = Nca(path, nca[1], keys, tib)
    print('[i] gen=%d rights=%s secs=%s IVFC sec%d' % (n.gen, n.rights.hex(),
          [(hex(a), hex(b)) for a, b in n.secs], n.sid))
    lv = [struct.unpack_from('<QQI', n.fsh, 0x18 + i * 0x18) for i in range(6)]
    comp = struct.unpack_from('<QQ', n.fsh, 0x178)
    print('[i] level5 @%#x size=%#x comp=%s' % (lv[5][0], lv[5][1], tuple(hex(x) for x in comp)))
    return n, SecView(n, lv[5][0]), comp


def main():
    path = sys.argv[1]
    args = sys.argv[2:]
    n, v, comp = open_nsp(path)
    if comp[0] or comp[1]:
        raise SystemExit('该 NCA 是压缩段，请改用 handsome_nca.py 套路')
    files, fd = parse_romfs(v)
    print('[i] romfs files=%d data_base=%#x' % (len(files), fd))
    filt = next((a.split('=', 1)[1] for a in args if a.startswith('--filter=')), None)
    if '--list' in args:
        for nm, o, s in files:
            if filt is None or filt.lower() in nm.lower():
                print('%12d  %s' % (s, nm))
        return
    if '--get' in args:
        sub = args[args.index('--get') + 1]
        out = args[args.index('--out') + 1]
        for nm, o, s in files:
            if sub.lower() in nm.lower():
                p = os.path.join(out, nm.replace('/', os.sep))
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, 'wb') as w:
                    for k in range(0, s, 1 << 23):
                        w.write(v.read(o + k, min(1 << 23, s - k)))
                print('   -> %s (%d)' % (nm, s))


if __name__ == '__main__':
    main()
