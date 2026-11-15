# -*- coding: utf-8 -*-
"""Adobe AIR / Flash 「*.kvs + *.dat」资源归档解包器

格式（实测，非标准 AMF3 —— 作者手写简化版）：
    kvs = raw deflate(zlib wbits=-15) 之后：
        0A 0B 01                       固定头
        { u29(len<<1)  name  u09 u29 u29  04 u29(off)  04 u29(size) } * N
        01                             结束标记
    dat = 各条目首尾相接，每条 [off, off+size) 各自再 raw deflate

用法：
    python scripts/air_kvs_dat.py <目录> [<输出目录>]
    # 目录内需有同名成对的 xxx.kvs / xxx.dat
    # 输出：<输出目录>/<kvs 名>/<条目名>（默认输出目录 = <目录>/_unpack）
"""
import os, sys, zlib


def u29(b, o):
    v = 0
    for i in range(4):
        x = b[o]; o += 1
        if i < 3:
            v = (v << 7) | (x & 0x7f)
            if not x & 0x80:
                return v, o
        else:
            return (v << 8) | x, o
    return v, o


def load_kvs(path):
    """返回 [(name, offset, size)]"""
    raw = open(path, 'rb').read()
    d = zlib.decompress(raw, -15)
    o = 3
    ents = []
    while o < len(d) and d[o] != 0x01:
        ln, o = u29(d, o)
        ln >>= 1
        name = d[o:o+ln].decode('utf-8', 'replace'); o += ln
        assert d[o] == 0x09, 'kvs 结构异常 @%d' % o
        o += 1
        _, o = u29(d, o)
        _, o = u29(d, o)
        vals = []
        for _ in range(2):
            assert d[o] == 0x04, 'kvs 结构异常 @%d' % o
            v, o = u29(d, o + 1); vals.append(v)
        ents.append((name, vals[0], vals[1]))
    return ents


def unpack_one(kvs_path, dat_path, out_dir):
    ents = load_kvs(kvs_path)
    blob = open(dat_path, 'rb').read()
    os.makedirs(out_dir, exist_ok=True)
    ok = raw_copy = 0
    for name, off, size in ents:
        chunk = blob[off:off + size]
        try:
            data = zlib.decompress(chunk, -15)
            ok += 1
        except zlib.error:
            data = chunk
            raw_copy += 1
        dst = os.path.join(out_dir, name.replace('/', os.sep))
        os.makedirs(os.path.dirname(dst) or out_dir, exist_ok=True)
        open(dst, 'wb').write(data)
    return len(ents), ok, raw_copy


def main():
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(src, '_unpack')
    pairs = [f[:-4] for f in os.listdir(src) if f.lower().endswith('.kvs')]
    if not pairs:
        print('未找到 *.kvs'); return 1
    for base in sorted(pairs):
        kvs = os.path.join(src, base + '.kvs')
        dat = os.path.join(src, base + '.dat')
        if not os.path.exists(dat):
            print('%-24s 缺 %s.dat，跳过' % (base, base)); continue
        n, ok, raw = unpack_one(kvs, dat, os.path.join(out, base))
        print('%-24s %5d 条（解压 %d / 原样 %d）→ %s' %
              (base, n, ok, raw, os.path.join(out, base)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
