#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CRAZY CHA!N -エルピスの鎖- (Switch XCI) → 切出 secure 分区内的 NCA

为什么需要它:
  `hactool -t xci` 对本 XCI 报 `XCI partition is corrupt!`。
  读 hactool 源码 `xci.c` 可知该报错来自 `check_memory_hash_table_with_suffix()`：
  用 header@0x140 的 `hfs0_header_hash` 校验 0xF000 处 0x200 字节的 root HFS0 头
  （可选 1 字节后缀 = compat type）。本机 keyset 无 `xci_header_key`，源码只试
  COMPAT_GLOBAL/CHINA 两个后缀，实测 0..255 全不中 ⇒ 无法通过校验。
  但**文件本身布局完全标准**，据此手工切出 NCA 即可（后续 `hactool -t nca` 一切正常）。

用法:
  python scripts/crazychain_xci.py --xci <path.xci> [--outdir _work_ccn/nca]
  python scripts/crazychain_xci.py --xci <path.xci> --list        # 只看结构
"""
import os
import re
import sys
import struct
import argparse

HFS0_HDR = 0x10
HFS0_ENT = 0x40


def read_hfs0(f, off):
    """返回 (entries, string_table, data_start)；entry = (offset, size, string_off, hashed_size, hash)"""
    f.seek(off)
    hdr = f.read(HFS0_HDR)
    if hdr[:4] != b'HFS0':
        raise ValueError('no HFS0 at 0x%X' % off)
    n, strsz, _pad = struct.unpack_from('<III', hdr, 4)
    ents = []
    f.seek(off + HFS0_HDR)
    for _ in range(n):
        e = f.read(HFS0_ENT)
        offs, size, stroff, hsz = struct.unpack_from('<QQII', e, 0)
        ents.append((offs, size, stroff, hsz, e[0x20:0x40]))
    st = f.read(strsz)
    return ents, st, off + HFS0_HDR + n * HFS0_ENT + strsz


def names_of(ents, st):
    out = []
    for off, size, stroff, hsz, h in ents:
        end = st.find(b'\0', stroff)
        out.append(st[stroff:end].decode('utf-8', 'replace'))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--xci', required=True)
    ap.add_argument('--outdir', default='_work_ccn/nca')
    ap.add_argument('--list', action='store_true')
    a = ap.parse_args()

    f = open(a.xci, 'rb')
    hdr = f.read(0x200)
    assert hdr[0x100:0x104] == b'HEAD', 'not an XCI (no HEAD @0x100)'
    hfs0_off, hfs0_size = struct.unpack_from('<QQ', hdr, 0x130)
    cart_type = hdr[0x10D]
    print('XCI: cart_type=0x%02X hfs0_offset=0x%X hfs0_size=0x%X' % (cart_type, hfs0_off, hfs0_size))

    ents, st, dstart = read_hfs0(f, hfs0_off)
    root_names = names_of(ents, st)
    print('root partitions:', root_names)

    if 'secure' not in root_names:
        print('!! no secure partition'); return 1
    i = root_names.index('secure')
    sec_off = dstart + ents[i][0]
    sec_size = ents[i][1]
    print('secure partition @0x%X size 0x%X' % (sec_off, sec_size))

    ents2, st2, dstart2 = read_hfs0(f, sec_off)
    nca_names = names_of(ents2, st2)
    os.makedirs(a.outdir, exist_ok=True)
    for k, (off, size, stroff, hsz, _h) in enumerate(ents2):
        abs_off = dstart2 + off
        print('  [%d] %-46s off=0x%-10X size=0x%-10X abs=0x%X' % (k, nca_names[k], off, size, abs_off))
        if a.list:
            continue
        dst = os.path.join(a.outdir, '%d_%s' % (k, nca_names[k]))
        f.seek(abs_off)
        left = size
        with open(dst, 'wb') as o:
            while left > 0:
                b = f.read(min(8 << 20, left))
                if not b:
                    break
                o.write(b)
                left -= len(b)
        print('      -> %s' % dst)
    f.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
