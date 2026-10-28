#!/usr/bin/env python3
"""dk_lib.py -- drastic Killer 容器库: ISO -> DATAxx.HD/BIN -> PACK -> 解压条目。"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from iso9660 import ISO
import ml2_tkl, ml2_type2

ISO_PATH = '_work_dk/dk.iso'
_iso = None


def iso():
    global _iso
    if _iso is None:
        _iso = ISO(ISO_PATH)
        _iso.root_map = {}
        for e in _iso.entries(_iso.root):
            n = e['name'].decode('latin1') if isinstance(e['name'], bytes) else e['name']
            _iso.root_map[n] = e
    return _iso


def grab(name):
    e = iso().root_map[name]
    iso().f.seek(e['lba'] * 2048)
    return iso().f.read(e['size'])


def hd_list(vol):
    """返回该卷 [bytes] 顶层文件。"""
    hd = grab(vol + '.HD')
    bn = grab(vol + '.BIN')
    sizes = list(struct.unpack('<%dI' % (len(hd) // 4), hd))
    pos, out = 0, []
    for s in sizes:
        out.append(bn[pos:pos + s])
        pos = (pos + s + 0x7ff) // 0x800 * 0x800
    assert pos == len(bn), (vol, pos, len(bn))
    return out


def unpack_pack(b):
    """PACK -> [(name, csize, usize, flags, raw_segment)]  (raw 已按 key 去 XOR)"""
    assert b[:4] == b'PACK', b[:8]
    nl = struct.unpack_from('<I', b, 4)[0]
    key = b[8:8 + nl]
    doff, dsz, off = struct.unpack_from('<3I', b, 8 + nl)
    cnt, rec = struct.unpack_from('<2I', b, 8 + nl + 20)
    ents = []
    for k in range(cnt):
        e = doff + rec * k
        d = b[e:e + rec]
        if nl:
            d = bytes(c ^ key[(rec * k + j) % nl] for j, c in enumerate(d))
        nm = d[:0x30].split(b'\x00')[0].decode('cp932', 'replace')
        o, cs, us, fl = struct.unpack_from('<4I', d, 0x30)
        seg = b[off + o:off + o + cs]
        if nl:
            seg = bytes(c ^ key[j % nl] for j, c in enumerate(seg))
        ents.append((nm, cs, us, fl, seg))
    return ents


def expand(seg, us, fl):
    t = fl & 0xF
    if t == 0:
        return seg
    if t == 1:
        return ml2_tkl.lzss(seg, us or None)
    if t == 2:
        return ml2_type2.decode(seg, us or None)
    raise ValueError('flags=%d' % fl)


def walk(vols=('DATA00', 'DATA01', 'DATA02', 'DATA03', 'DATA04', 'DATA05', 'DATA06', 'DATA07')):
    """yield (vol, name, csize, usize, flags, raw_segment)"""
    for vol in vols:
        for b in hd_list(vol):
            if b[:4] != b'PACK':
                continue
            for r in unpack_pack(b):
                yield (vol,) + r
