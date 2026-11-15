#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[JP]Ariard-少年アリス - Under the rose  data.xp3 解析 / 抽取

KiriKiri XP3 的「保护归档」变体（由 plugin/ariard.tpm 定制）：

  header(40 B): magic(11)=b'XP3\r\n \n\x1a\x8bg\x01' + 21 B 保留 + index_offset(u64 @0x20)
  index      : u8 flag(=1) + u64 comp_size + u64 orig_size + zlib 流（位于文件尾部）
  流内       : 多个 'File' chunk，每个 File 含 'info' / 'segm' / 'adlr' 子块
  'info'     : flags u32 + orig u64 + arc u64 + namelen u16 + name(UTF-16LE)   ← 仅取名字
  'segm'     : flags u32 + offset u64 + **orig u64 + stored u64**              ← 顺序是 orig 在前！
  'adlr'     : 4 B，**首字节 = 本文件 XOR 密钥**，其余 3 B 未知

  载荷变换：plain = XOR( zlib?( stored_bytes ) , key )   —— key = adlr[0]
    flags(segm) == 1 → 先 zlib 解压（压缩后大小 = stored，原始大小 = orig）
    flags(segm) == 0 → 原样，直接 XOR（此时 orig == stored）

  ※ 注意与标准 XP3 的两处差异：
    1) segm 的 size 字段是 orig 在前、stored 在后（标准常写作 comp/orig，此处反了）
    2) 所有文件载荷都被逐字节单字节 XOR 混淆，密钥藏在 adlr 首字节
    3) 索引偏移在 0x20，不在 0x0B

用法:
  python scripts/ariard_xp3.py list <xp3> [名字过滤]
  python scripts/ariard_xp3.py x    <xp3> <outdir> [名字过滤]
  python scripts/ariard_xp3.py raw  <xp3> <name> [outfile]     # 解单文件到 stdout/文件
"""
import struct
import sys
import os
import zlib

MAGIC = b'XP3\r\n \n\x1a\x8bg\x01'


def load(path):
    d = open(path, 'rb').read()
    assert d[:11] == MAGIC, 'not XP3 magic'
    io = struct.unpack_from('<Q', d, 0x20)[0]
    flag = d[io]
    csz = struct.unpack_from('<Q', d, io + 1)[0]
    osz = struct.unpack_from('<Q', d, io + 9)[0]
    assert flag == 1, 'index flag=%d (未压缩索引不支持)' % flag
    idx = zlib.decompressobj().decompress(d[io + 17:io + 17 + csz])
    assert len(idx) == osz, ('index size', len(idx), osz)
    return d, idx


def parse(idx):
    """返回 [(name, [(flags, off, orig, stored)], adlr_bytes|None)]"""
    out = []
    p = 0
    while p + 12 <= len(idx):
        typ = idx[p:p + 4]
        sz = struct.unpack_from('<Q', idx, p + 4)[0]
        body = idx[p + 12:p + 12 + sz]
        if typ != b'File':
            raise RuntimeError('unexpected chunk %r at %#x' % (typ, p))
        q = 0
        name = None
        segs = []
        adlr = None
        while q + 12 <= len(body):
            t = body[q:q + 4]
            s = struct.unpack_from('<Q', body, q + 4)[0]
            bd = body[q + 12:q + 12 + s]
            if t == b'info':
                nl = struct.unpack_from('<H', bd, 20)[0]
                name = bd[22:22 + nl * 2].decode('utf-16-le', 'replace')
            elif t == b'segm':
                i = 0
                while i + 28 <= len(bd):
                    fl = struct.unpack_from('<I', bd, i)[0]
                    off, orig, stored = struct.unpack_from('<QQQ', bd, i + 4)
                    segs.append((fl, off, orig, stored))
                    i += 28
            elif t == b'adlr':
                adlr = bd
            q += 12 + s
        out.append((name, segs, adlr))
        p += 12 + sz
    return out


def decode(entry, d):
    name, segs, adlr = entry
    key = adlr[0] if adlr else 0
    parts = []
    for fl, off, orig, stored in segs:
        raw = d[off:off + stored]
        if fl == 1:
            raw = zlib.decompressobj().decompress(raw)
        if len(raw) != orig:
            raise RuntimeError('%s seg size %d != orig %d' % (name, len(raw), orig))
        parts.append(bytes([b ^ key for b in raw]))
    return b''.join(parts)


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return 1
    cmd = a[0]
    if cmd == 'list':
        d, idx = load(a[1])
        flt = a[2] if len(a) > 2 else ''
        tot = 0
        n_hit = 0
        for name, segs, adlr in parse(idx):
            if flt and flt.lower() not in (name or '').lower():
                continue
            sz = sum(s[2] for s in segs)
            tot += sz
            z = sum(1 for s in segs if s[0] == 1)
            print('%-56s %10d segs=%d z=%d key=%s' % (
                name, sz, len(segs), z,
                adlr[:1].hex() if adlr else '--'))
            n_hit += 1
        print('--- %d / %d 文件, %d B' % (n_hit, len(parse(idx)), tot))
        return 0
    if cmd == 'x':
        d, idx = load(a[1])
        outdir = a[2]
        flt = a[3] if len(a) > 3 else ''
        n_ok = 0
        for e in parse(idx):
            name = e[0]
            if flt and flt.lower() not in (name or '').lower():
                continue
            # 伪条目：插件塞进来的版权警告，不是真文件
            if not name or name.startswith('$$$') or not e[1]:
                print('[skip]', (name or '')[:40])
                continue
            buf = decode(e, d)
            # Windows 路径清洗：非法字符 + 超长名
            safe = name
            for ch in ':?*"<>|':
                safe = safe.replace(ch, '_')
            comps = safe.split('/')
            comps = [c if len(c) <= 120 else c[:110] + '_%d' % len(c) for c in comps]
            safe = '/'.join(comps)
            dst = os.path.join(outdir, safe.replace('/', os.sep))
            os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
            open(dst, 'wb').write(buf)
            n_ok += 1
        print('extracted', n_ok)
        return 0
    if cmd == 'raw':
        d, idx = load(a[1])
        for e in parse(idx):
            if e[0] == a[2]:
                buf = decode(e, d)
                if len(a) > 3:
                    open(a[3], 'wb').write(buf)
                    print('wrote', a[3], len(buf))
                else:
                    sys.stdout.buffer.write(buf)
                return 0
        print('not found:', a[2])
        return 1
    print(__doc__)
    return 1


if __name__ == '__main__':
    sys.exit(main())
