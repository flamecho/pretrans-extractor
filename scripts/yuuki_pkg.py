#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yuuki! Novel (ゆうき！ノベル) 引擎 —— 容器 PackageFile20 解析 + 文件解密。

引擎识别：可执行文件内出现 `PackageFile20` 与 `YuukiNovel WorkFile`（Delphi 编译，作者 結城陸）。

两个独立能力：
  scan(data)        扫 exe 里所有 PackageFile20 容器，返回目录记录
  decrypt(blk)      LCG + XOR 解密（seed 前置 4 字节）

LCG 参数来自反汇编：
  seed = u32 @blk[0:4]
  for each byte: state = (state * 0x6C078965 + 1) & 0xFFFFFFFF; out = blk[i] ^ (state >> 24)

目录布局（实测，见 解析报告/[JP]alto -アルト-_解析报告.md）：
  魔数 `\\x0cPackageFile20\\0` 紧跟 `\\x0b` + 首个内部文件名（头槽名）
  记录区 = N 条定长 264 B，名字起点 np = magic_off + 0x118 + 264*i
  记录解析（以名字起点 np 为锚）：
      off  = u32 @ np-9
      size = u32 @ np-5
      nlen = u8  @ np-1
      name = np .. np+nlen            (cp932)
  数据区基准 base 需由首个文件魔数反推（各作不同）：
      content(i) 起点 = base + off(i+1)   ← 名字与内容差一条记录
"""
import struct

MAGIC = b'\x0cPackageFile20\x00'
REC = 264


def scan(d):
    """返回 dict: {magic_off, base_guess_unused, recs:[(idx,name,off,size)]}"""
    mo = d.find(MAGIC)
    if mo < 0:
        return None
    np0 = mo + 0x118                      # 名字起点，实测偏移
    recs = []
    for i in range(512):
        np = np0 + REC * i
        if np + 1 > len(d):
            break
        nlen = d[np - 1]
        if nlen == 0 or nlen > 200:
            break
        off, size = struct.unpack_from('<II', d, np - 9)
        raw = d[np:np + nlen]
        if off > 0x40000000 or size > 0x40000000:
            break
        recs.append((i, raw, off, size))
    return {'magic_off': mo, 'np0': np0, 'recs': recs}


def guess_base(d, recs, lo=0x0, hi=None, shift=0):
    """用图片魔数反推数据区基准 base（唯一未知量）。

    判据：content(i) 起点 = base + off(i+1)，其前 3/8 字节应为 jpg/png 魔数。
    票数最高的 base 即真值（alto 实测 46/46 全中）。返回 (base, hits, total)。
    """
    hi = hi if hi is not None else min(len(d) - 8, 0x200000)
    pairs = []                       # (name[i], off[i+1]) —— 名字与内容差一条记录
    for k in range(len(recs) - 1):
        nm = name_of(recs[k][1]).lower()
        if nm.endswith(('.jpg', '.png')):
            pairs.append((nm, recs[k + 1][2]))
    best, bestn = None, -1
    for base in range(lo, min(lo + 0x4000, hi)):
        hit = 0
        for nm, off in pairs:
            p = base + off
            if p + 8 > len(d):
                continue
            sig = d[p:p + 8]
            if nm.endswith('.jpg') and sig[:3] == b'\xff\xd8\xff':
                hit += 1
            elif nm.endswith('.png') and sig == b'\x89PNG\r\n\x1a\n':
                hit += 1
        if hit > bestn:
            best, bestn = base, hit
    return best, bestn, len(pairs)


def decrypt(blk):
    """LCG + XOR；blk[0:4] 为 seed。返回明文 bytes。"""
    if len(blk) < 8:
        return b''
    state = struct.unpack_from('<I', blk, 0)[0]
    out = bytearray(len(blk) - 4)
    for i in range(4, len(blk)):
        state = (state * 1812433253 + 1) & 0xFFFFFFFF
        out[i - 4] = blk[i] ^ (state >> 24)
    return bytes(out)


def name_of(raw):
    for enc in ('cp932', 'utf-8'):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.hex()


if __name__ == '__main__':
    import sys
    p = sys.argv[1]
    d = open(p, 'rb').read()
    info = scan(d)
    print('magic_off=0x%X  recs=%d' % (info['magic_off'], len(info['recs'])))
    tot = 0
    for i, raw, off, size in info['recs']:
        tot += size
        print('%2d off=%08x size=%8d %s' % (i, off, size, name_of(raw)))
    print('sum size =', tot)
