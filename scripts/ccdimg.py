#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CloneCD / raw-2352 光盘镜像 → ISO9660 目录树 list / extract（不落整盘 ISO 副本）。

判据（L0，字节层）：
  · 扇区 2352B：sync(12 `00 FF*10 00`) + header(4) + **MODE1 user data @+16** / **MODE2 @+24** + EDC/ECC(288)
  · PVD 在**扇区 16**（user data 起 'CD001'@+1，volume id @+40）
  · 目录记录：`[len(1)][ext_attr(1)][extent_LBA(4 LE)][size(4 LE)][date(7)][flags(1)][unit(1)][gap(1)][volseq(2)][nameLen(1)][name…]`
    flags bit1=目录；name `0x00`=`.`、`0x01`=`..`；文件名为 `NAME;1` 形式

★ 位移镜像（`--shift N`）：有些镜像在数据区前面插了垃圾扇区，而 ISO9660 里的 extent LBA
  没跟着改。判据不是猜：**同一镜像里两处独立的已知明文锚点算出的差值必须相同**，再用第三个
  文件的魔数（MZ / OLE / MSCF…）验证。
  实例（24時、君のハートは盗まれる～怪盗ジェイド～ 盘1）：`op.mpg` 的 MPEG pack 头
  (`00 00 01 BA`) 首个出现在 raw 9,480,928 = 4031×2352+16，而 extent=2031 ⇒ +2000；
  `jade01.dat` 的 `YKC001` 在 81626×2352+16，extent=79626 ⇒ +2000；两点一致，
  7 个文件（Thumbs.db→OLE、AUTORUN.INF→`[autorun]`、jade.exe/SetUp.exe/DSETUP.dll→MZ、
  SetUp.lst→`F\tjade.exe`、jade01.dat→YKC001）全部命中。目录项本身在插入点之前，不受影响。

用法：
  python scripts/ccdimg.py <img>                      # 列目录树
  python scripts/ccdimg.py <img> --out DIR            # 全量解出
  python scripts/ccdimg.py <img> --out DIR --only "dat/;sce"   # 只解路径含任一关键字的
  python scripts/ccdimg.py <img> --shift 2000         # 数据区整体后移 2000 扇区
  python scripts/ccdimg.py <img> --sector 2048        # 若镜像本身是 2048B/扇区（普通 ISO）

不写中间 ISO：按 extent 直接把 2048B 块拼出来，省一份整盘副本。
"""
import argparse
import os
import struct
import sys

SYNC = b'\x00' + b'\xff' * 10 + b'\x00'


class Raw:
    def __init__(self, path, sector=0, user_off=None):
        self.f = open(path, 'rb')
        self.f.seek(0, 2)
        self.size = self.f.tell()
        # 自动判型：有 sync + header + mode 字节 ⇒ raw；否则当纯 ISO（2048）
        head = self._head(32)
        if sector in (0, None):
            sector = 2352 if head[:12] == SYNC else 2048
        self.ss = sector
        if user_off is None:
            user_off = 0 if sector == 2048 else (24 if head[15] == 2 else 16)
        self.uo = user_off
        self.mode = 0 if sector == 2048 else head[15]
        self.nsec = self.size // sector

    def _head(self, n):
        pos = self.f.tell()
        self.f.seek(0)
        b = self.f.read(n)
        self.f.seek(pos)
        return b

    def sector(self, n):
        self.f.seek(n * self.ss)
        b = self.f.read(self.ss)
        return b[self.uo:self.uo + 2048]

    def read(self, lba, size, shift=0):
        out = bytearray()
        for i in range((size + 2047) // 2048):
            out += self.sector(lba + shift + i)
        return bytes(out[:size])


def records(data):
    """遍历一个目录块（可能跨多扇区，已拼好）里的目录记录。"""
    i = 0
    while i < len(data):
        ln = data[i]
        if ln == 0:
            # 记录不跨扇区：跳到下一个 2048 边界
            i = (i // 2048 + 1) * 2048
            continue
        rec = data[i:i + ln]
        ext = struct.unpack('<I', rec[2:6])[0]
        size = struct.unpack('<I', rec[10:14])[0]
        flags = rec[25]
        nl = rec[32]
        name = rec[33:33 + nl]
        i += ln
        if nl == 1 and name in (b'\x00', b'\x01'):
            continue
        yield ext, size, flags, name


def walk(img, lba=0, size=0, prefix='', out=None, only=(), shift=0):
    if size == 0:
        pvd = img.sector(16)
        # 根目录记录自 156 起：len(1)+extattr(1) ⇒ extent_LBA 在 +2（LE），size 在 +10（LE）
        lba = struct.unpack('<I', pvd[158:162])[0]
        size = struct.unpack('<I', pvd[166:170])[0]
    data = img.read(lba, size)          # 目录在位移点之前，不加 shift
    for ext, sz, flags, raw in records(data):
        name = raw.decode('cp932', 'replace')
        if ';' in name:
            name = name.split(';')[0]
        path = prefix + name
        if flags & 0x02:
            walk(img, ext, sz, path + '/', out, only, shift)
        else:
            keep = (not only) or any(k.lower() in path.lower() for k in only)
            mark = '' if keep else '  (skip)'
            if out and keep:
                dst = os.path.join(out, path.replace('/', os.sep))
                os.makedirs(os.path.dirname(dst) or out, exist_ok=True)
                open(dst, 'wb').write(img.read(ext, sz, shift))
                print('%10d  LBA %-7d %s' % (sz, ext, path))
            else:
                print('%10d  LBA %-7d %s%s' % (sz, ext, path, mark))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('img')
    ap.add_argument('--out')
    ap.add_argument('--only', default='', help='分号分隔关键字：路径含任一才解出')
    ap.add_argument('--sector', type=int, default=0, help='0=自动；2352（raw）或 2048（纯 ISO）')
    ap.add_argument('--user-off', type=int, default=None, help='user data 偏移；默认按 MODE 判（1→16, 2→24）')
    ap.add_argument('--shift', type=int, default=0, help='数据区 LBA 整体后移的扇区数（目录项不变）')
    a = ap.parse_args()
    only = [x.strip() for x in a.only.split(';') if x.strip()]
    img = Raw(a.img, a.sector, a.user_off)
    print('# %s  %d B  %d sectors × %d  MODE%s user@+%d  shift=%d'
          % (os.path.basename(a.img), img.size, img.nsec, img.ss,
             img.mode if img.mode else 'ISO', img.uo, a.shift))
    if a.out:
        os.makedirs(a.out, exist_ok=True)
    walk(img, out=a.out, only=only, shift=a.shift)


if __name__ == '__main__':
    sys.exit(main())
