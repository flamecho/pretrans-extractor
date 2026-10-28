#!/usr/bin/env python3
"""tennis_unpack.py -- [PS2-JP] テニスの王子様 RUSH & DREAM! 解包.

容器: <NAME>.HD(u32 尺寸表, 记录在 <NAME>.BIN 中 2048 对齐)
      条目 0 = FILENAME.LST(名字与后续条目一一对应)
      PACK: 'PACK'|u32 0|u32 dirOff|u32 dirSize|u32 dataOff|u32 dataSize|u32 ?|u32 count|u32 64|u32 0
            目录 64B: name[0x30]|u32 off|csize|usize|flags   (off 相对 dataOff)
      flags&0xF: 0=store, 1=LZSS, 2=type2

用法:
  python scripts/tennis_unpack.py list  <bin>
  python scripts/tennis_unpack.py dump  <bin> [outdir] [filter...]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ml2_type2 import decode as t2decode
from ml2_tkl import lzss

SEC = 2048


def hd_entries(binpath):
    hdp = os.path.splitext(binpath)[0] + '.HD'
    hd = open(hdp, 'rb').read()
    v = list(struct.unpack('<%dI' % (len(hd) // 4), hd))
    off, offs = 0, []
    for s in v:
        offs.append(off)
        off = (off + s + SEC - 1) // SEC * SEC
    f = open(binpath, 'rb')
    names = [l for l in f.read(v[0]).decode('cp932').split('\r\n') if l]
    assert len(names) == len(v), (len(names), len(v))
    return names, offs, v, f


def pak_entries(d):
    _, dirOff, dirSize, dataOff, dataSize, _, count, esize, _ = struct.unpack_from('<9I', d, 4)
    assert d[:4] == b'PACK'
    out = []
    for k in range(count):
        e = d[dirOff + k * esize: dirOff + (k + 1) * esize]
        nm = e[:0x30].split(b'\0')[0].decode('cp932')
        off, csize, usize, fl = struct.unpack_from('<4I', e, 0x30)
        out.append((nm, dataOff + off, csize, usize, fl))
    return out


def unpack_entry(d, off, csize, usize, fl):
    src = d[off:off + csize]
    t = fl & 0xF
    if t == 0:
        return src
    if t == 1:
        return lzss(src, usize)
    if t == 2:
        return t2decode(src, usize)
    raise ValueError('flag %d' % fl)


def main():
    cmd = sys.argv[1]
    binp = sys.argv[2]
    names, offs, sizes, f = hd_entries(binp)
    if cmd == 'list':
        for i, n in enumerate(names):
            print(i, n, sizes[i])
        return
    outdir = sys.argv[3]
    filt = sys.argv[4:]
    os.makedirs(outdir, exist_ok=True)
    for i, n in enumerate(names):
        if filt and not any(k.lower() in n.lower() for k in filt):
            continue
        f.seek(offs[i])
        d = f.read(sizes[i])
        if d[:4] != b'PACK':
            p = os.path.join(outdir, n.replace('\\', '_'))
            open(p, 'wb').write(d)
            continue
        sub = os.path.join(outdir, n.replace('\\', '_'))
        os.makedirs(sub, exist_ok=True)
        for nm, off, csize, usize, fl in pak_entries(d):
            try:
                out = unpack_entry(d, off, csize, usize, fl)
            except Exception as e:
                print('!', n, nm, e)
                continue
            if usize and len(out) != usize:
                print('!size', n, nm, len(out), usize)
            open(os.path.join(sub, nm.replace('\\', '_')), 'wb').write(out)
    print('done')


if __name__ == '__main__':
    main()
