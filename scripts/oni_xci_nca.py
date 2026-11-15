#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""XCI → 就地读 NCA → RomFS 枚举/导出（不过 hactool，不落 NCA）。

背景：nsz 重打包的 XCI 会触发 hactool 的 `XCI partition is corrupt!`；
`xci_romfs.py` 又用 hdr[0x206] 当 keygen（本作真值在 u32@0x220&0xFF = 18），
解不出 key_area ⇒ 复用 `nsp_nca_romfs.Romfs`（keygen 取 0x220、KAEK = _<keygen-1>）。

用法:
  python scripts/oni_xci_nca.py <x.xci> --list
  python scripts/oni_xci_nca.py <x.xci> --getall --out-dir _w_oni/romfs
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import switch_nca as S
import nsp_nca_romfs as M

KEYS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '_sw', 'prod_fixed.keys')


def find_nca(path):
    """扫 XCI 前 64MB 的 HFS0（secure 分区），返回 (off, size)。"""
    with open(path, 'rb') as f:
        buf = f.read(64 << 20)
    i = buf.find(b'HFS0')
    best = None
    while i >= 0:
        try:
            num, strsz = struct.unpack_from('<II', buf, i + 4)
            if not (0 < num < 4096 and 0 < strsz < (1 << 20)):
                raise ValueError
            ent = i + 0x10
            names = buf[ent + num * 0x40:ent + num * 0x40 + strsz]
            data = ent + num * 0x40 + strsz
            for k in range(num):
                off, size, no, _h = struct.unpack_from('<QQII', buf, ent + k * 0x40)
                name = names[no:names.find(b'\0', no)].decode('utf-8', 'replace')
                if name.endswith('.nca') and (best is None or size > best[1]):
                    best = (data + off, size)
        except Exception:
            pass
        i = buf.find(b'HFS0', i + 4)
    return best


class F:
    def __init__(self, p):
        self.f = open(p, 'rb')

    def tik_for(self, r):
        return None


def open_xci(path, keys_path=KEYS):
    keys = M.load_keys(keys_path)
    off, size = find_nca(path)
    d = F(path)
    d.f.seek(off)
    hk = bytes.fromhex(keys['header_key'])
    hdr = S.xts_decrypt(hk[:16], hk[16:], 0, d.f.read(0x1600))
    assert hdr[0x200:0x204] == b'NCA3', 'NCA 头解密失败'
    return M.Romfs(d, off, hdr, keys), off, size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('xci')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--getall', action='store_true')
    ap.add_argument('--out-dir')
    ap.add_argument('--filter', default='')
    a = ap.parse_args()
    rf, off, size = open_xci(a.xci)
    print('[i] nca off=%#x size=%#x  keygen=%d slot=%s romfs_abs=%#x' % (
        off, size, rf.keygen, getattr(rf, 'key_slot', None), rf.romfs_abs))
    ents = list(rf.entries())
    files = [e for e in ents if e[0] == 'file']
    orp = rf.orphans()
    print('[i] dirs=%d files=%d orphans=%d total=%d' % (
        len(ents) - len(files), len(files), len(orp), sum(e[3] for e in files) + sum(o[2] for o in orp)))
    if a.list:
        for t, p, o, s in ents:
            if a.filter and a.filter not in p:
                continue
            print('%-4s %10d %s' % (t, s, p))
        for nm, doff, dsize in orp:
            print('ORPH %10d %s' % (dsize, nm))
    if a.getall:
        assert a.out_dir, '--getall 需要 --out-dir'
        for t, p, o, s in ents:
            if t != 'file':
                continue
            rel = p.lstrip('/')
            dst = os.path.join(a.out_dir, rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as w:
                w.write(rf.file_bytes(o, s))
        for nm, doff, dsize in orp:
            dst = os.path.join(a.out_dir, '_orphan', nm.replace('/', os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as w:
                w.write(rf.file_bytes(doff, dsize))
        print('[ok] 已导出到', a.out_dir)


if __name__ == '__main__':
    main()
