#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[JP]Angel ★ Pop  data.xp3 索引解析 / 抽取

旧版 XP3（KiriKiri 1.x 形态）：
  header: magic(11) + index_offset(u64)
  index : flag(u8=1) + comp_size(u64) + orig_size(u64) + zlib 流
  流内  : 多个 'File' chunk（**一条一个**），每个 'File' 内再套 'info'/'segm'/'adlr'
  'info': flags u32 + orig u64 + arc u64 + namelen u16 + name(UTF-16LE)
  'segm': flags u32 + offset u64 + orig u64 + arc u64
用法:
  python scripts/angelpop_xp3.py list  <xp3>
  python scripts/angelpop_xp3.py x     <xp3> <outdir> [子串过滤]
"""
import struct, zlib, sys, os

MAGIC = b'XP3\r\n \n\x1a\x8bg\x01'


def load_index(path):
    d = open(path, 'rb').read()
    assert d[:11] == MAGIC, 'not XP3 at 0'
    io = struct.unpack_from('<Q', d, 0x0b)[0]
    flag = d[io]
    assert flag == 1, 'flag=%d (不支持未压缩索引)' % flag
    csz, osz = struct.unpack_from('<QQ', d, io + 1)
    idx = zlib.decompressobj().decompress(d[io + 17:io + 17 + csz])
    assert len(idx) == osz, (len(idx), osz)
    return d, idx


def parse(idx):
    files = []
    p = 0
    while p + 12 <= len(idx):
        typ = idx[p:p + 4]
        sz = struct.unpack_from('<Q', idx, p + 4)[0]
        body = idx[p + 12:p + 12 + sz]
        if typ != b'File':
            raise RuntimeError('unexpected chunk %r at %#x' % (typ, p))
        # 逐个子块
        q = 0
        name = None
        segs = []
        while q + 12 <= len(body):
            t = body[q:q + 4]
            s = struct.unpack_from('<Q', body, q + 4)[0]
            bd = body[q + 12:q + 12 + s]
            if t == b'info':
                fl, orig, arc = struct.unpack_from('<IQQ', bd, 0)
                nl = struct.unpack_from('<H', bd, 20)[0]
                name = bd[22:22 + nl * 2].decode('utf-16-le')
            elif t == b'segm':
                fl = struct.unpack_from('<I', bd, 0)[0]
                off, orig, arc = struct.unpack_from('<QQQ', bd, 4)
                segs.append((off, orig, arc, fl))   # fl=0 原样 / fl=1 zlib
            q += 12 + s
        files.append((name, segs))
        p += 12 + sz
    return files


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return 1
    cmd = a[0]
    d, idx = load_index(a[1])
    files = parse(idx)
    if cmd == 'list':
        flt = a[2] if len(a) > 2 else ''
        tot = 0
        for n, s in files:
            if flt and flt.lower() not in (n or '').lower():
                continue
            sz = sum(x[1] for x in s)
            tot += sz
            cz = sum(1 for x in s if x[3])
            print('%-52s %10d  segs=%d z=%d' % (n, sz, len(s), cz))
        print('--- 命中 %d / 总计 %d 文件, %d B' % (
            sum(1 for n, s in files if not flt or flt.lower() in (n or '').lower()),
            len(files), tot))
        return 0
    if cmd == 'x':
        outdir = a[2]
        flt = a[3] if len(a) > 3 else ''
        n_ok = 0
        for n, s in files:
            if flt and flt.lower() not in (n or '').lower():
                continue
            if not n or not s:
                print('[skip]', n)
                continue
            parts = []
            for o, orig, arc, fl in s:
                raw = d[o:o + arc]
                if fl == 1:
                    raw = zlib.decompressobj().decompress(raw)
                assert len(raw) == orig, (n, len(raw), orig)
                parts.append(raw)
            buf = b''.join(parts)
            dst = os.path.join(outdir, n.replace('/', os.sep))
            os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
            open(dst, 'wb').write(buf)
            n_ok += 1
        print('extracted', n_ok)
        return 0
    print('unknown cmd')
    return 1


if __name__ == '__main__':
    sys.exit(main())
