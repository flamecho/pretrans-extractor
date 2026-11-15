#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FORIS-OS（0verflow 系／S.S.D.S. 等）PACK（`*.CMP`）解包器。

格式（2026-11-03 依 Nenkai/FORISOSUnpacker `Formats/Pack/PackFile.cs` 的参考实现移植；MIT）
  · `*.CMP` = 一个 UPX 压过的空壳 DLL ＋ **尾部附加数据**（壳只为防直接打开，不含正文）。
  · 文件**末 8 字节**：`[u32 加密 magic][u32 TOC 偏移]`；magic 用 16 字节密钥循环 XOR 后应等于 `"PACK"`。
  · TOC 在 `tocOffset`：`i32 解压后长度` ＋ 到（文件长−8）为止的密文；XOR 后 **LZ 解压**。
  · TOC 条目（10 字节头）：`i32 文件偏移｜u8 名长(字符数)｜u8 压缩标志(bit0=1 表示 LZ)｜i32 未知｜UTF-16LE 名`；
    条目流以**名字为空**的哨兵结束；每条的压缩长度 = 下一条偏移 − 本条偏移 − (压缩时 4 字节长度头)。
  · 压缩文件体 = `i32 解压后长度` ＋ LZ 数据。
  · LZ（`DecompressLZ`）：逐 token 读 1 字节 `bits`
      `bits & 0x80` ⇒ 取 2 字节 `all = bits<<8 | 下一字节`：`backOffset = all & 0x7FF`（**本作 11 位；参考实现写的
        10 位 `0x3FF` 只适用于别的 build**）、`len = ((all >> 11) & 0xF) * 2 + 2`，从 `out - backOffset - 1` 复制（可重叠）
      否则 ⇒ **字面量段**，长度 `bits + 1` 字节。
    ⇒ 每个 token 的字面量段最多 128 字节，且 `0x80` 起的 token 一定是回溯。

XOR 密钥 = `ssds.exe` 里名为 `Binary` 的 RCDATA（0x10 字节）。本作实测：
  `F5 CD 8C 8B DB D7 82 3D 6F 6B A4 C7 04 D6 6B BB`

用法
  python scripts/foris_pack.py list  <x.CMP>
  python scripts/foris_pack.py x     <x.CMP> <outdir> [--only 关键字;关键字]
"""
import argparse
import os
import struct
import sys

KEY = bytes([0xF5, 0xCD, 0x8C, 0x8B, 0xDB, 0xD7, 0x82, 0x3D,
             0x6F, 0x6B, 0xA4, 0xC7, 0x04, 0xD6, 0x6B, 0xBB])
MAGIC = b'PACK'


def crypt(buf: bytearray, key=KEY):
    for i in range(len(buf)):
        buf[i] ^= key[i % 16]
    return buf


def lz_decompress(src, size):
    out = bytearray(size)
    o = 0
    i = 0
    n = len(src)
    while o < size:
        bits = src[i]; i += 1
        if bits & 0x80:
            allb = (bits << 8) | src[i]; i += 1
            back = allb & 0x7FF                      # 11 位距离（见文件头注释）
            length = ((allb >> 11) & 0xF) * 2 + 2
            if o + length > size:
                length = size - o
            prev = o - back - 1
            for _ in range(length):
                out[o] = out[prev]; o += 1; prev += 1
        else:
            length = bits + 1
            if o + length > size:
                length = size - o
            out[o:o + length] = src[i:i + length]
            i += length; o += length
    return bytes(out)


def read_toc(path):
    d = open(path, 'rb').read()
    magic = bytearray(d[-8:-4])          # ⚠ bytearray 切片是副本，必须整体 crypt 后再用
    crypt(magic)
    if bytes(magic) != MAGIC:
        raise SystemExit('不是 FORIS-OS PACK（末 8 字节解出 %r ≠ PACK）' % bytes(magic))
    toc_off = struct.unpack_from('<i', d, len(d) - 4)[0]
    dec_size = struct.unpack_from('<i', d, toc_off)[0]
    body = bytearray(d[toc_off + 4:len(d) - 8])
    crypt(body)
    toc = lz_decompress(bytes(body), dec_size)
    ent = []
    p = 0
    while p < len(toc):
        off, nlen, flags, unk = struct.unpack_from('<iBBI', toc, p)
        name = toc[p + 10:p + 10 + nlen * 2].decode('utf-16le', 'replace')
        p += 10 + nlen * 2
        ent.append({'off': off, 'flags': flags, 'unk': unk, 'name': name})
        if not name.strip():
            break
    for k in range(len(ent) - 1):
        hdr = 4 if (ent[k]['flags'] & 1) else 0
        ent[k]['csize'] = ent[k + 1]['off'] - ent[k]['off'] - hdr
    return d, ent[:-1]


def extract(path, d, e):
    o = e['off']
    if e['flags'] & 1:
        size = struct.unpack_from('<i', d, o)[0]
        return lz_decompress(d[o + 4:o + 4 + e['csize']], size)
    return d[o:o + e['csize']]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('list', 'x'))
    ap.add_argument('pack')
    ap.add_argument('outdir', nargs='?')
    ap.add_argument('--only', help='分号分隔关键字：名字含任一才解')
    a = ap.parse_args()
    d, ent = read_toc(a.pack)
    if a.cmd == 'list':
        for e in ent:
            print('%10d  f=%d  csize=%-8d %s' % (e['off'], e['flags'], e['csize'], e['name']))
        print('共 %d 条' % len(ent))
        return
    keys = [k for k in (a.only or '').split(';') if k]
    n = 0
    for e in ent:
        if keys and not any(k in e['name'] for k in keys):
            continue
        p = os.path.join(a.outdir, e['name'].replace('\\', '/'))
        os.makedirs(os.path.dirname(p) or '.', exist_ok=True)
        data = extract(a.pack, d, e)
        open(p, 'wb').write(data)
        n += 1
    print('解出 %d 个文件 → %s' % (n, a.outdir))


if __name__ == '__main__':
    main()
