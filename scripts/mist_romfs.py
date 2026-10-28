#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ミストニアの翅望 —— 压缩 NCA(BKTR/LZ4 bucket-tree) → RomFS 直读（复用 redbell_romfs 的桶树实现）。

实测参数（XCI @0x1f022 的 Program NCA）：
  sec1 @0x1c000 size 0x1aea80000 | ctr_hi 0x0000000200000000
  key = AES_dec(key_area_key_application_11, ka[2]) = e371f3351010a31e74a4d2d49d48c2a5
  IVFC level5 @0xf14000 | CompressionInfo TableOffset 0x1ad85c760 (BKTR), 82 桶, 解压总长 0x1df87e538
用法:
  python scripts/mist_romfs.py --list
  python scripts/mist_romfs.py --get <outdir> [名子串...]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import redbell_romfs as R

R.NSP = '_w_W1_mist/Wings Of Mistonia The Lost Delight[01007AD01CB42000][1.0.0][0][16.0.0].xci'
R.NCA_BASE = 0x1f022
R.SEC1_OFF = 0x1c000
R.SEC1_SIZE = 0x1aea80000
R.CTR_HI = bytes.fromhex('0000000200000000')
R.KEY = bytes.fromhex('e371f3351010a31e74a4d2d49d48c2a5')
R.LEVEL5 = 0xf14000
R.TBL_OFF = 0x1ad85c760

if __name__ == '__main__':
    R.main()
