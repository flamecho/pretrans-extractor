#!/usr/bin/env python3
"""ml2_tkl.py -- [PS2-JP] マイネリーベII tkl 容器 + type-2 解压 全链路工具.

容器: DATA0x.HD(u32 尺寸表, 记录在 DATA0x.BIN 中 2048 对齐) -> PACK -> 条目
条目 flags&0xF: 0=store, 1=LZSS, 2=dictionary/grammar(见 ml2_type2.py)

用法:
  python scripts/ml2_tkl.py dump <srcdir> <outdir>       # 全量解出
  python scripts/ml2_tkl.py list <srcdir>               # 统计
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ml2_type2 import decode as t2decode   # noqa: E402

SEC = 2048


def hd_records(hd_path, bin_size):
    v = list(struct.unpack('<%dI' % (os.path.getsize(hd_path) // 4),
                           open(hd_path, 'rb').read()))
    offs, o = [], 0
    for s in v:
        offs.append(o)
        o = (o + s + SEC - 1) // SEC * SEC
    assert o == bin_size, 'HD/BIN size mismatch %d != %d' % (o, bin_size)
    return v, offs


def lzss(src, size=None):
    """flags=1: LZSS 变体（逆向自 SLPM_662.47 0x136070，原机逐字节验证）。

    [u32 N][(N+7)/8 个标志字节][比特流]；标志字节 LSB 优先
      bit=1 -> 1 字节字面量
      bit=0 -> u16le: dist=(v>>4)&0xfff, len=(v&0xF)+2；dist==0 即结束标记
    4096 环形缓冲，**写指针初值 1**，读地址 = (dist+i)&0xfff。
    """
    n = struct.unpack_from('<I', src, 0)[0]
    nb = (n + 7) // 8
    p = 4 + nb
    ring = bytearray(4096)
    w = 1
    fb = 0
    bit = 8
    fi = 0
    out = bytearray()
    while True:
        if bit == 8:
            if 4 + fi >= 4 + nb:
                raise ValueError('lzss: flag byte overrun')
            fb = src[4 + fi]
            fi += 1
            bit = 0
        if (fb >> bit) & 1:
            c = src[p]; p += 1
            ring[w & 0xfff] = c
            w += 1
            out.append(c)
        else:
            v = src[p] | (src[p + 1] << 8)
            p += 2
            dist = (v >> 4) & 0xfff
            ln = (v & 0xf) + 2
            if dist == 0:
                break
            for i in range(ln):
                c = ring[(dist + i) & 0xfff]
                ring[w & 0xfff] = c
                w += 1
                out.append(c)
        bit += 1
    if size is not None and len(out) != size:
        raise ValueError('lzss: size %d != usize %d' % (len(out), size))
    return bytes(out)


def entries_of(b):
    """PACK -> [dict(name, off, csize, usize, flags, raw)]"""
    if b[:4] != b'PACK':
        raise ValueError('not PACK')
    nl = struct.unpack_from('<I', b, 4)[0]
    name = b[8:8 + nl]
    dirOff, dirSize, dataOff, dataSize, _u, cnt = struct.unpack_from('<6I', b, 8 + nl)
    ents = []
    for k in range(cnt):
        e = dirOff + 64 * k
        d = bytes(b[e + j] ^ name[(64 * k + j) % nl] for j in range(64)) if nl else b[e:e + 64]
        no, cs, us, fl = struct.unpack_from('<4I', d, 0x30)
        seg = b[dataOff + no: dataOff + no + cs]
        if nl:
            seg = bytes(c ^ name[j % nl] for j, c in enumerate(seg))
        ents.append({'name': d[:0x30].split(b'\x00')[0].decode('cp932', 'replace'),
                     'off': no, 'csize': cs, 'usize': us, 'flags': fl & 0xf, 'raw': seg})
    return ents, {'name': name, 'count': cnt, 'dataOff': dataOff}


def expand(ent):
    """解压单条目 -> bytes"""
    t = ent['flags']
    if t == 0:
        return ent['raw']
    if t == 1:
        return lzss(ent['raw'], ent['usize'] or None)
    if t == 2:
        return t2decode(ent['raw'], ent['usize'] or None)
    raise ValueError('flags=%d unknown' % t)


def walk(srcdir, outdir, log=print):
    stats = {'ok': 0, 'fail': 0, 'bytes': 0}
    for dn in ('DATA00', 'DATA01', 'DATA02', 'DATA03', 'DATA04'):
        hd = os.path.join(srcdir, dn + '.HD')
        bn = os.path.join(srcdir, dn + '.BIN')
        if not os.path.exists(hd) or not os.path.exists(bn):
            continue
        sizes, offs = hd_records(hd, os.path.getsize(bn))
        blob = open(bn, 'rb').read()
        lst = [l for l in blob[offs[0]:offs[0] + sizes[0]].decode('cp932', 'replace')
               .replace('\r\n', '\n').split('\n') if l]
        for i, sz in enumerate(sizes):
            if i == 0:
                continue
            nm = lst[i] if i < len(lst) else '%s_%03d.bin' % (dn, i)
            data = blob[offs[i]:offs[i] + sz]
            if data[:4] != b'PACK':
                continue
            try:
                ents, info = entries_of(data)
            except Exception as e:
                log('!! %s/%s: %s' % (dn, nm, e))
                stats['fail'] += 1
                continue
            base = os.path.join(outdir, dn, nm.rsplit('.', 1)[0])
            os.makedirs(base, exist_ok=True)
            _dump(ents, base, log, stats)


def _dump(ents, base, log, stats, depth=0):
    for en in ents:
        try:
            out = expand(en)
        except Exception as e:
            log('!! %s/%s: %s' % (base, en['name'], e))
            stats['fail'] += 1
            continue
        if out[:4] == b'PACK' and depth < 3:
            sub = os.path.join(base, en['name'].rsplit('.', 1)[0] + '_')
            os.makedirs(sub, exist_ok=True)
            try:
                e2, _ = entries_of(out)
                _dump(e2, sub, log, stats, depth + 1)
                continue
            except Exception:
                pass
        path = os.path.join(base, en['name'])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, 'wb').write(out)
        stats['ok'] += 1
        stats['bytes'] += len(out)


if __name__ == '__main__':
    if sys.argv[1] == 'dump':
        srcdir, outdir = sys.argv[2], sys.argv[3]
        st = {'ok': 0, 'fail': 0, 'bytes': 0}
        walk(srcdir, outdir)
    else:
        print(__doc__)
