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
            # ★ 判 MODE1/MODE2 只能看 header 的 mode byte（第 15 字节）：
            #   同步头 `00 FF×10 00` 两种模式**完全一样**，用 `s[0]==0 and s[1:4]==FF` 会
            #   把**所有 MODE1 盘**都判成 MODE2（本作 2026-11-04 [JP]JACKIN 实测：
            #   每扇区多跳 8 字节 ⇒ ISO 全盘位移，7z 直接打不开）。
            mode = s[15]
            off = 24 if mode == 2 else 16
            fo.write(s[off:off + 2048])
    print('sectors=%d -> %s (%d B)' % (n, dst, os.path.getsize(dst)))

if __name__ == '__main__':
    conv(sys.argv[1], sys.argv[2])
