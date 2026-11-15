#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CloneCD / 裸镜像 → ISO9660 目录树（支持 raw-2352 MODE1 与 2048 纯数据）

用法:
    python scripts/clonecd_iso.py <img> --list              # 列目录（制表格式）
    python scripts/clonecd_iso.py <img> -x OUTDIR           # 解出到目录
    python scripts/clonecd_iso.py <img> --sector 2352 --user-off 16

为什么要单独一个工具：
  · 7-Zip **打不开** raw-2352 的 .img（`Cannot open the file as archive`，本作 7z 24.09 实测）；
  · 本类镜像（CloneCD `MODE1/2352`）扇区 = 2352 B，user data 在扇区内 **+16**，不做重排也能直读；
  · 目录名常为 SJIS 长名 ⇒ 走 **Joliet SVD**（LBA 17，UCS-2BE），primary 树只有 8.3 名。
"""
import argparse
import os
import struct
import sys

SEC_USER = {2352: 16, 2336: 8, 2048: 0}     # MODE1 raw / MODE2 raw / 纯数据


class Iso:
    def __init__(self, path, sector=None, user_off=None):
        self.f = open(path, 'rb')
        self.size = os.path.getsize(path)
        if sector is None:
            # 2352 优先（CD 镜像绝大多数如此），其次 2048
            for s in (2352, 2336, 2048):
                if self.size % s == 0:
                    sector = s
                    break
            else:
                raise SystemExit('无法判定扇区大小：%d B' % self.size)
        self.sec = sector
        self.off = SEC_USER[sector] if user_off is None else user_off
        self.nsec = self.size // sector
        self.joliet = None
        for lba in (16, 17, 18):
            d = self.raw(lba)
            if d[1:6] != b'CD001':
                continue
            if d[0] == 1 and self.joliet is None:
                self.pvd = (lba, d)
            if d[0] == 2 and d[88:91] in (b'%/@', b'%/C', b'%/E'):
                self.joliet = (lba, d)
        if not hasattr(self, 'pvd'):
            raise SystemExit('LBA16 不是 CD001 主卷描述符：扇区/偏移参数不对')
        # Romeo 型（SVD 带 Joliet 转义但名字却是 8bit SJIS，本作实测）vs 真 Joliet（UCS-2BE）
        self.ucs2 = False
        if self.joliet:
            for rec in self._recs(struct.unpack_from('<I', self.pvd[1], 158)[0],
                                  struct.unpack_from('<I', self.pvd[1], 166)[0]):
                ln = rec[32]
                nb = rec[33:33 + ln]
                if ln > 1 and nb not in (b'\x00', b'\x01'):
                    self.ucs2 = all(b == 0 for b in nb[1::2])
                    break

    def raw(self, lba):
        self.f.seek(lba * self.sec + self.off)
        n = 2048 if self.off else self.sec
        return self.f.read(n)

    # ---- 目录记录 ----
    def _recs(self, lba, length):
        data = b''.join(self.raw(lba + i) for i in range((length + 2047) // 2048))
        data = data[:length]
        p = 0
        while p < len(data):
            ln = data[p]
            if ln == 0:
                p = (p // 2048 + 1) * 2048      # 扇区内剩余为填充
                continue
            yield data[p:p + ln]
            p += ln

    def _name(self, rec):
        ln = rec[32]
        nb = rec[33:33 + ln]
        if ln == 1 and nb in (b'\x00', b'\x01'):
            return None                              # '.' / '..'
        if self.ucs2 and len(nb) % 2 == 0:
            s = nb.decode('utf-16-be', 'replace')
        else:
            s = nb.decode('cp932', 'replace')        # 8.3 名里塞 SJIS 双字节（本类盘常见）
        return s.split(';')[0]

    def walk(self, lba=None, length=None, prefix=''):
        if lba is None:
            # PVD @156 是根目录**记录**（34 B）：记录内 extent @+2、data length @+10
            lba, length = struct.unpack_from('<I', self.pvd[1], 158)[0], \
                          struct.unpack_from('<I', self.pvd[1], 166)[0]
        for rec in self._recs(lba, length):
            nm = self._name(rec)
            if nm is None:
                continue
            elba = struct.unpack_from('<I', rec, 2)[0]
            elen = struct.unpack_from('<I', rec, 10)[0]
            flags = rec[25]
            path = prefix + nm
            if flags & 2:
                yield from self.walk(elba, elen, path + '/')
            else:
                yield path, elba, elen


def main():
    ap = argparse.ArgumentParser(description='CloneCD/ISO 镜像 → ISO9660 目录树')
    ap.add_argument('img')
    ap.add_argument('--sector', type=int, help='扇区字节数（默认自动：2352/2336/2048）')
    ap.add_argument('--user-off', type=int, help='扇区内 user data 偏移（默认按扇区推）')
    ap.add_argument('--list', action='store_true', help='列目录（制表格式）')
    ap.add_argument('-x', '--extract', metavar='OUTDIR', help='解出到目录')
    a = ap.parse_args()

    iso = Iso(a.img, a.sector, a.user_off)
    ents = list(iso.walk())
    if a.list or not a.extract:
        print('# %s  %d B  %d sectors × %d  user@+%d  树=%s' % (
            os.path.basename(a.img), iso.size, iso.nsec, iso.sec, iso.off,
            'Joliet' if iso.joliet else 'primary'))
        for path, lba, size in sorted(ents, key=lambda e: e[0]):
            print('%10d  LBA %-7d  %s' % (size, lba, path))
        print('# 文件 %d 个' % len(ents))
    if a.extract:
        n = 0
        for path, lba, size in ents:
            dst = os.path.join(a.extract, *path.split('/'))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as w:
                left = size
                cur = lba
                while left > 0:
                    blk = iso.raw(cur)[:min(left, 2048)]
                    w.write(blk)
                    left -= len(blk)
                    cur += 1
            n += 1
        print('解出 %d 个文件 → %s' % (n, a.extract))
    return 0


if __name__ == '__main__':
    sys.exit(main())
