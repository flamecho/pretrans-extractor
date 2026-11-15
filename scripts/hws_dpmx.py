# -*- coding: utf-8 -*-
"""HWS（Hunks Workshop! / エフジー）DPMX 容器解包。

格式（2026-11-04 实证，HWS0/HWS3 两款互验）:
  0x00  'DPMX'
  0x04  u32 index_off      # 数据区起点
  0x08  u32 count          # 条目数（含 1 条哨兵，末条常非法）
  0x0C  u32 0
  0x10  count × 32 字节条目：
          +0x00 char[16] 文件名（cp932，NUL 填）
          +0x10 u32      0xFFFFFFFF（目录标志；文件恒为此值）
          +0x14 u32      0
          +0x18 u32      offset = **相对 index_off**
          +0x1C u32      size
用法:
  python scripts/hws_dpmx.py list <dat>
  python scripts/hws_dpmx.py extract <dat> <outdir>
"""
import io
import os
import struct
import sys


def parse(path):
    d = io.open(path, 'rb').read()
    magic = d[:4]
    if magic != b'DPMX':
        raise SystemExit('不是 DPMX: %r' % magic)
    idx, cnt, _ = struct.unpack('<III', d[4:16])
    out = []
    for i in range(cnt):
        o = 0x10 + 32 * i
        if o + 32 > idx:
            break
        name = d[o:o + 16].split(b'\0')[0].decode('cp932', 'replace')
        flag, _, off, size = struct.unpack('<IIII', d[o + 16:o + 32])
        if not name:
            continue
        a = idx + off
        if size == 0 or a + size > len(d):
            continue
        out.append((name, a, size, flag))
    return d, idx, cnt, out


def main():
    mode = sys.argv[1]
    d, idx, cnt, ents = parse(sys.argv[2])
    if mode == 'list':
        print('index_off=%#x count=%d 有效条目=%d 文件 %d B' % (idx, cnt, len(ents), len(d)))
        for nm, a, s, f in ents:
            print('  %-16s off=%08x size=%8d' % (nm, a, s))
        print('字节和 %d（数据区 %d）' % (sum(s for _, _, s, _ in ents), len(d) - idx))
        return
    out = sys.argv[3]
    os.makedirs(out, exist_ok=True)
    for nm, a, s, f in ents:
        p = os.path.join(out, nm.replace('\\', '_').replace('/', '_'))
        io.open(p, 'wb').write(d[a:a + s])
    print('解出 %d 个文件 → %s' % (len(ents), out))


if __name__ == '__main__':
    main()
