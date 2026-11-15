# -*- coding: utf-8 -*-
"""JACKIN.img（CloneCD raw-2352 MODE1，LBA24 后插 2000 扇区）→ 按路径提取文件。
用法: python jk_extract.py <img> <outdir> [name-filter]
"""
import sys, os, struct

SHIFT, CUT = 2000, 24


class Img:
    def __init__(self, path):
        self.f = open(path, 'rb')

    def sector(self, lba):
        phys = lba + SHIFT if lba >= CUT else lba
        self.f.seek(phys * 2352)
        s = self.f.read(2352)
        return s[16:16 + 2048]

    def read(self, lba, size):
        out = bytearray()
        while size > 0:
            s = self.sector(lba)
            n = min(size, 2048)
            out += s[:n]
            size -= n
            lba += 1
        return bytes(out)


def rec(d):
    ln = d[0]
    if ln < 34:
        return None
    lba = struct.unpack_from('<I', d, 2)[0]
    size = struct.unpack_from('<I', d, 10)[0]
    fl = d[25]
    nl = d[32]
    return lba, size, fl, d[33:33 + nl].decode('cp932', 'replace').split(';')[0]


def walk(img, lba, size, prefix, out, filt):
    data = img.read(lba, size)
    p = 0
    while p < len(data):
        if data[p] == 0:
            p = (p // 2048 + 1) * 2048
            continue
        r = rec(data[p:p + 300])
        if not r:
            p += 1
            continue
        p += data[p]
        l2, s2, f2, n2 = r
        if n2 in ('\x00', '\x01', ''):
            continue
        path = prefix + n2
        if f2 & 2:
            walk(img, l2, s2, path + '/', out, filt)
        else:
            if filt and not filt(path):
                continue
            out.append((path, l2, s2))


def main():
    img = Img(sys.argv[1])
    outdir = sys.argv[2]
    filt = None
    if len(sys.argv) > 3:
        keys = sys.argv[3].split(',')
        filt = lambda p: any(k in p for k in keys)
    root = rec(img.sector(16)[156:156 + 300])
    files = []
    walk(img, root[0], root[1], '', files, filt)
    print('files', len(files))
    for path, lba, size in files:
        dst = os.path.join(outdir, path.replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True) if os.path.dirname(dst) else None
        with open(dst, 'wb') as fo:
            fo.write(img.read(lba, size))
        print('%-40s %9d' % (path, size))


if __name__ == '__main__':
    main()
