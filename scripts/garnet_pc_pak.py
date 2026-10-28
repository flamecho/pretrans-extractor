#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GsWin / DataPack5 (Takuyo PC) —— .pak 解包 + Scw5.x 脚本解码。

格式来源（参考实现）：
  regomne/lneditor  lnMels/GsWin/GsWin/GsWin.cpp  (ScwHeader / GsDecrypt / GsLzssUncompress)
  本脚本据此重写为 Python，并按实测 .pak 结构补出 DataPack5 容器层。

DataPack5 容器（实测 GARNET CRADLE / GARNET CRADLE Sugary Sparkle）
  0x000 "DataPack5\0\0\0" + title[32]（=0x2c）
  0x30  u32 version(0x00050001)  0x34 u32 toc_size  0x38 u32 0
  0x3c  u32 block_count          0x40 u32 data_start(0x800)  0x44 u32 toc_offset
  [0x800 .. toc_offset)  = block_count 个 Scw 块（见下）
  [toc_offset .. EOF)    = TOC：LZSS（无 xor）压缩，解压后 block_count × 0x68
                           entry[0x00..0x40] = 名称 NUL 填充；[0x40]=offset [0x44]=size ...

Scw 块（0x1C8 头 + 负载，负载 4 字节对齐）
  0x00 magic[0x10]="Scw5.x\0..."
  0x10 u16 minor  0x12 u16 major(=5)
  0x14 u32 is_compr (-1=压缩)
  0x18 u32 uncomprlen  0x1c u32 comprlen
  0x20 u32 always_1
  0x24 u32 inst_table_entries  0x28 u32 str_table_entries  0x2c u32 unk_table_entries
  0x30 u32 inst_data_len       0x34 u32 str_data_len       0x38 u32 unk_data_len
  0x3c u32 unk1                0x40 u32 status_block_len  0x44 pad[0x184]
  负载 = GsDecrypt(xor i&0xff) → GsLzssUncompress(uncomprlen)
  解压后：inst_table(n×8) str_table(n×8) unk_table(n×8) inst_data str_data unk_data

用法:
  python scripts/garnet_pc_pak.py <pak 或目录> <输出目录>
"""
import os
import struct
import sys

WIN = 4096


def gs_decrypt(buf):
    b = bytearray(buf)
    for i in range(len(b)):
        b[i] ^= i & 0xFF
    return bytes(b)


def lzss(src, outlen):
    dst = bytearray()
    win = bytearray(WIN)
    wp = 0xFEE
    cur = 0
    flag = 0
    n = len(src)
    while len(dst) < outlen:
        flag >>= 1
        if not (flag & 0x100):
            if cur >= n:
                break
            flag = src[cur] | 0xFF00
            cur += 1
        if flag & 1:
            if cur >= n:
                break
            d = src[cur]
            cur += 1
            win[wp] = d
            wp = (wp + 1) & (WIN - 1)
            dst.append(d)
        else:
            if cur + 1 >= n:
                break
            off = src[cur] | ((src[cur + 1] & 0xF0) << 4)
            ln = (src[cur + 1] & 0x0F) + 3
            cur += 2
            for i in range(ln):
                if len(dst) >= outlen:
                    break
                d = win[(off + i) & (WIN - 1)]
                dst.append(d)
                win[wp] = d
                wp = (wp + 1) & (WIN - 1)
    return bytes(dst)


def read_pak(path):
    d = open(path, 'rb').read()
    assert d[:9] == b'DataPack5', path
    toc_size, _zero, block_count, data_start = struct.unpack_from('<4I', d, 0x34)
    toc_off = struct.unpack_from('<I', d, 0x44)[0]
    toc_raw = lzss(d[toc_off:], block_count * 0x68)
    toc = []
    for i in range(block_count):
        e = toc_raw[i * 0x68:(i + 1) * 0x68]
        name = e[:0x40].split(b'\0')[0].decode('cp932', 'replace')
        toc.append((name, e))
    off = data_start
    blocks = []
    for i in range(block_count):
        h = d[off:off + 0x1C8]
        unc, comp, always1 = struct.unpack_from('<3I', h, 0x18)
        body = d[off + 0x1C8: off + 0x1C8 + comp]
        blocks.append((toc[i][0], h, body, unc, comp))
        off += 0x1C8 + ((comp + 3) // 4 * 4)
    assert off == toc_off, (hex(off), hex(toc_off))
    return d, toc, blocks


def read_scw(h, body):
    unc, comp, always1 = struct.unpack_from('<3I', h, 0x18)
    n_i, n_s, n_u, l_i, l_s, l_u = struct.unpack_from('<6I', h, 0x24)
    compr = struct.unpack_from('<I', h, 0x14)[0]
    if compr == 0xFFFFFFFF:
        raw = lzss(gs_decrypt(body), unc)
    else:
        raw = gs_decrypt(body[:unc])
    assert len(raw) == unc, (len(raw), unc)
    p = 0
    itab = [struct.unpack_from('<II', raw, p + 8 * k) for k in range(n_i)]
    p += 8 * n_i
    stab = [struct.unpack_from('<II', raw, p + 8 * k) for k in range(n_s)]
    p += 8 * n_s
    utab = [struct.unpack_from('<II', raw, p + 8 * k) for k in range(n_u)]
    p += 8 * n_u
    inst = raw[p:p + l_i]
    p += l_i
    strs = raw[p:p + l_s]
    p += l_s
    unk = raw[p:p + l_u]
    return dict(itab=itab, stab=stab, utab=utab, inst=inst, strs=strs, unk=unk, raw=raw)


def getstr(scw, idx):
    off, ln = scw['stab'][idx]
    return scw['strs'][off:off + ln].decode('cp932', 'replace')


def main():
    src = sys.argv[1]
    outdir = sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    paks = []
    if os.path.isdir(src):
        for f in sorted(os.listdir(src)):
            if f.lower().endswith('.pak'):
                paks.append(os.path.join(src, f))
    else:
        paks = [src]
    for pak in paks:
        d, toc, blocks = read_pak(pak)
        base = os.path.splitext(os.path.basename(pak))[0]
        od = os.path.join(outdir, base)
        os.makedirs(od, exist_ok=True)
        print('%-14s blocks=%d toc=%d' % (base, len(blocks), len(toc)))
        for i, (name, h, body, unc, comp) in enumerate(blocks):
            fn = os.path.join(od, '%03d_%s.scw' % (i, name.replace('/', '_').replace('\\', '_')))
            try:
                scw = read_scw(h, body)
            except Exception as e:
                print('  ERR', i, name, e)
                continue
            with open(fn, 'wb') as fw:
                fw.write(h)
                fw.write(scw['raw'])
        # 名称表
        with open(os.path.join(od, '_names.txt'), 'w', encoding='utf-8') as fw:
            for i, (name, e) in enumerate(toc):
                fw.write('%03d\t%s\n' % (i, name))


if __name__ == '__main__':
    main()
