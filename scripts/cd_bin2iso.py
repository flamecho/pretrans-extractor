# -*- coding: utf-8 -*-
"""MODE1/2352 · MODE2/2352 裸镜像 -> 2048 用户数据 ISO

用法: python scripts/cd_bin2iso.py <in.bin> <out.iso>
MODE2 Form1: 每扇区 2352 B，用户数据在 +24；用同步头 00 FF..FF 00 判定。
"""
import sys, os

def conv(src, dst):
    n = os.path.getsize(src) // 2352
    with open(src, 'rb') as fi, open(dst, 'wb') as fo:
        for i in range(n):
            fi.seek(i * 2352)
            s = fi.read(2352)
            if len(s) < 2352:
                break
            if s[0] == 0 and s[1:4] == b'\xff\xff\xff':
                fo.write(s[24:24 + 2048])   # MODE2 Form1
            else:
                fo.write(s[16:16 + 2048])   # MODE1
    print('sectors=%d -> %s (%d B)' % (n, dst, os.path.getsize(dst)))

if __name__ == '__main__':
    conv(sys.argv[1], sys.argv[2])
