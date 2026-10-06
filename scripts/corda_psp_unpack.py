#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
金色のコルダ (PSP) 容器解包 : ISO9660 -> CDVDAR.DAR (Koei CDAR v2) -> 嵌套 DAR
================================================================
用法:
  python corda_psp_unpack.py iso <金色のコルダ.iso> <outdir>      # 解 ISO9660
  python corda_psp_unpack.py cdar <CDVDAR.DAR> <outdir>          # 解 CDAR v2 (含嵌套)

CDAR v2 (小端序):
  0x00 "CDAR" | u32 version(=2) | u32 unk | u32 hash
  0x10 cdartree_t : u32 count | u32×3        -> 节点自 0x20 起, 每 16 字节
  node(16B): u32 nameOffset | u8 datatype | u8 zsize[3] | u32 dataOffset | u32 dataSize
      datatype==1 -> 子目录 (dataOffset 指向另一棵 tree)
      datatype&2  -> zlib 压缩 (实际压缩长度 = zsize)
"""
import os, sys, struct, zlib


# ---------------- ISO9660 ----------------
def iso_walk(f, lba, size, prefix, out):
    f.seek(lba * 2048)
    buf = f.read(size)
    i = 0
    while i < len(buf):
        rl = buf[i]
        if rl == 0:
            i = ((i // 2048) + 1) * 2048
            continue
        if i + rl > len(buf):
            break
        rec = buf[i:i + rl]
        ext = rec[25]
        nlen = rec[32]
        name = rec[33:33 + nlen]
        off = struct.unpack_from('<I', rec, 2)[0]
        sz = struct.unpack_from('<I', rec, 10)[0]
        if nlen == 1 and name[0] in (0, 1):
            i += rl
            continue
        nm = name.decode('latin1').rstrip(';1').rstrip('.')
        full = prefix + '/' + nm
        if ext & 2:
            out.append((full + '/', off, sz, 2))
            iso_walk(f, off, sz, full, out)
        else:
            out.append((full, off, sz, 0))
        i += rl


def iso_entries(path):
    f = open(path, 'rb')
    f.seek(16 * 2048)
    d = f.read(2048)
    assert d[1:6] == b'CD001', 'not ISO9660'
    rec = d[156:190]
    out = []
    iso_walk(f, struct.unpack_from('<I', rec, 2)[0],
             struct.unpack_from('<I', rec, 10)[0], '', out)
    return f, out


def iso_extract(iso, outdir):
    f, ents = iso_entries(iso)
    n = 0
    for p, off, sz, fl in ents:
        if fl == 2:
            continue
        dest = os.path.join(outdir, p.lstrip('/'))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        f.seek(off * 2048)
        with open(dest, 'wb') as g:
            g.write(f.read(sz))
        n += 1
    print(f'ISO: {n} files -> {outdir}')


# ---------------- CDAR v2 ----------------
class Node(struct.Struct):
    def __init__(self, data, offset):
        super().__init__("<IB3B2I")
        (self.nameoffset, self.datatype, d1, d2, d3,
         self.dataoffset, self.datasize) = self.unpack_from(data[offset:])
        self.datazsize = d1 + (d2 << 8) + (d3 << 16)
        self.subtree = None
        nend = data.find(b'\0', self.nameoffset)
        self.name = bytes(data[self.nameoffset:nend]).decode('latin1')
        if self.datatype == 1:
            self.subtree = Tree(data, self.dataoffset)


class Tree(struct.Struct):
    def __init__(self, data, offset):
        super().__init__("<4I")
        (self.count, _, _, _) = self.unpack_from(data[offset:])
        self.nodes = [Node(data, offset + self.size + i * 0x10)
                      for i in range(self.count)]


def cdar_flat(data):
    res = []

    def rec(tree, path):
        for n in tree.nodes:
            p = path + '/' + n.name
            if n.subtree is not None:
                rec(n.subtree, p)
            else:
                res.append((p, n))
    rec(Tree(data, 16), '')
    return res


def cdar_extract(path, outdir, nested=True):
    data = open(path, 'rb').read()
    assert data[:4] == b'CDAR', 'not CDAR'
    imgs = []
    for p, n in cdar_flat(data):
        if n.datatype & 2:
            c = zlib.decompress(data[n.dataoffset:n.dataoffset + n.datazsize])
        else:
            c = data[n.dataoffset:n.dataoffset + n.datasize]
        dest = os.path.join(outdir, p.replace('\\', '/').lstrip('/'))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, 'wb').write(c)
        if nested and c[:4] == b'CDAR':
            imgs.append(dest)
    print(f'CDAR: extracted -> {outdir} (nested {len(imgs)})')
    for d in imgs:
        cdar_extract(d, d + '.extracted')


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'iso':
        iso_extract(sys.argv[2], sys.argv[3])
    elif cmd == 'cdar':
        cdar_extract(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
