#!/usr/bin/env python3
"""[DEPRECATED] 已被 ml2_tkl.py 取代（本文件的 flags=1 LZSS / flags=2 实现均不正确）。

ml2_unpack.py -- [PS2-JP] マイネリーベII PACK/Konami-HD 解包器.

Container chain (verified 2026-10-22):
  DATA0x.HD  = u32[] size table; data at 2048-aligned offsets in DATA0x.BIN
  DATA0x.BIN record 0 = FILENAME.LST (CRLF cp932), record i = file i

  PACK file:
    0x00 'PACK'
    0x04 u32 nameLen
    0x08 name[nameLen]            <- XOR-protect code
    +0   u32 dirOff               (absolute)
    +4   u32 dirSize              = count * 64
    +8   u32 dataOff              (absolute)
    +12  u32 dataSize
    +16  u32 ?
    +20  u32 count
    +24  u32 64
    +28  u32 0
    目录  count * 64B entries (XOR-protected, phase 0 at dirOff):
           name[48] | u32 off | u32 csize | u32 usize | u32 flags
    data  每 entry 从 dataOff+off 起，**XOR 相位在该 entry 起点重置为 0**

  Protect: b ^= name[j % nameLen]   (j = 段内/条目内偏移)
  flags & 0xF: 0 = store, 1 = LZSS(4096,flag-first), 2 = alt-compressor
  LZSS: [u32 usize][(usize+7)/8 flag bytes][stream]
        bit=1 literal, bit=0 match = u16 (dist=v>>4, len=(v&0xF)+1), LSB-first
"""
import os
import re
import struct
import sys

SEC = 2048


def hd_records(hd_path, bin_size):
    v = list(struct.unpack('<%dI' % (os.path.getsize(hd_path) // 4),
                           open(hd_path, 'rb').read()))
    offs, o = [], 0
    for s in v:
        offs.append(o)
        o = (o + s + SEC - 1) // SEC * SEC
    return v, offs


def lzss(src, size=None):
    if size is None:
        size = struct.unpack_from('<I', src, 0)[0]
    nb = (size + 7) // 8
    flags = src[4:4 + nb]
    p = 4 + nb
    ring = bytearray(4096)
    w = 0
    out = bytearray()
    fb = 0
    bit = 8
    while len(out) < size:
        if bit == 8:
            if not flags:
                break
            fb = flags[0]
            flags = flags[1:]
            bit = 0
        if (fb >> bit) & 1:
            bit += 1
            if p >= len(src):
                break
            c = src[p]
            p += 1
            ring[w & 0xfff] = c
            w += 1
            out.append(c)
        else:
            bit += 1
            if p + 1 >= len(src):
                break
            v = src[p] | (src[p + 1] << 8)
            p += 2
            off = (v >> 4) & 0xfff
            ln = (v & 0xf) + 1
            for i in range(ln):
                c = ring[(off + i) & 0xfff]
                ring[w & 0xfff] = c
                w += 1
                out.append(c)
                if len(out) >= size:
                    break
    return bytes(out)


def parse_pack(b):
    """-> (entries, info). entry = dict(name,off,csize,usize,flags,data)"""
    if b[:4] != b'PACK':
        raise ValueError('not PACK')
    nl = struct.unpack_from('<I', b, 4)[0]
    name = b[8:8 + nl]
    f = struct.unpack_from('<8I', b, 8 + nl)
    dirOff, dirSize, dataOff, dataSize, _, cnt = f[0], f[1], f[2], f[3], f[4], f[5]
    ents = []
    for k in range(cnt):
        e = dirOff + 64 * k
        d = bytes(b[e + j] ^ name[(64 * k + j) % nl] for j in range(64)) if nl else b[e:e + 64]
        no, cs, us, fl = struct.unpack_from('<4I', d, 0x30)
        ents.append({'name': d[:0x30].split(b'\x00')[0].decode('cp932', 'replace'),
                     'off': no, 'csize': cs, 'usize': us, 'flags': fl})
    for en in ents:
        seg = b[dataOff + en['off']: dataOff + en['off'] + en['csize']]
        seg = bytes(c ^ name[j % nl] for j, c in enumerate(seg)) if nl else seg
        t = en['flags'] & 0xf
        if t == 0:
            en['data'] = seg
        elif t == 1:
            en['data'] = lzss(seg)
        elif t == 2:
            en['data'] = lzss(seg)          # alt scheme: same header, see report
        else:
            en['data'] = seg
    return ents, {'name': name, 'count': cnt, 'dataSize': dataSize}


def main():
    hd, binp, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    v, offs = hd_records(hd, os.path.getsize(binp))
    d = open(binp, 'rb').read()
    names = d[:v[0]].decode('cp932', 'replace').split('\r\n')
    os.makedirs(outdir, exist_ok=True)
    ok = bad = 0
    for i in range(1, len(v)):
        b = d[offs[i]:offs[i] + v[i]]
        nm = names[i] if i < len(names) else 'rec%d' % i
        try:
            ents, info = parse_pack(b)
        except Exception as e:
            print('skip', i, nm, e)
            bad += 1
            continue
        base = os.path.join(outdir, '%02d_%s' % (i, nm.replace('/', '_')))
        os.makedirs(base, exist_ok=True)
        for en in ents:
            safe = re.sub(r'[^0-9A-Za-z._-]', '_', en['name'])[:40] or ('e%d.bin' % ok)
            fn = os.path.join(base, safe)
            with open(fn, 'wb') as fo:
                fo.write(en['data'])
            ok += 1
        print('%-22s %3d entries' % (nm, len(ents)))
    print('entries written:', ok, 'bad packs:', bad)


if __name__ == '__main__':
    main()
