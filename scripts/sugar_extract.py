#!/usr/bin/env python3
"""sugar_extract.py —— PS2 シュガシュガルーン 恋もおしゃれもピックアップ！
DATA_PS2.AFS → 45 个 PAC（0x0425 文本指令流）→ 正文/选项文本。

指令格式（L0 证据）：
  [u16 0x0025][u16 sub][payload]   —— 控制/演出
  [u16 0x0425][u16 sub][payload]
     sub=1 名前札（独立名札窗，丢弃）
     sub=2 正文（NUL 结尾 cp932，带 &S..H..R..G..B..# 前缀与 &/# 后缀）
     sub=6 菜单/标签（丢弃）
断框：gap 含 0x0425/4（清窗）或 0x0025/1（等待点击）⇒ 新框；相邻无指令 ⇒ 同框排版换行
     （一次点击＝一行，框内换行直接拼接进同一行）。
"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import struct
import sys

ISO = os.path.join(VNTRANS_HOME, "_work_sugar/Sugar^2 Rune - Koi mo Oshare mo Pick-Up (Japan).iso")
AFS_LBA = 58665
OUT = os.path.join(VNTRANS_HOME, "_work_sugar/pac")
SEC = 2048


def afs_table(f):
    f.seek(AFS_LBA * SEC)
    h = f.read(8 + 7077 * 8)
    n = struct.unpack_from('<I', h, 4)[0]
    ent = [struct.unpack_from('<II', h, 8 + i * 8) for i in range(n)]
    return ent


def main():
    f = open(ISO, 'rb')
    ent = afs_table(f)
    os.makedirs(OUT, exist_ok=True)
    names = [i for i in range(7026, 7073) if i not in (7048, 7071)]
    for i in names:
        o, s = ent[i]
        f.seek(AFS_LBA * SEC + o)
        d = f.read(s)
        open(os.path.join(OUT, 'pac_%04d.bin' % i), 'wb').write(d)
    print('extracted', len(names))


if __name__ == '__main__':
    main()
