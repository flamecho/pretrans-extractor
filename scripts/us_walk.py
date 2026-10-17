#!/usr/bin/env python3
"""Parse .NET #US heap of a PE assembly and dump the ordered string sequence.
Usage: us_walk.py <dll> [start_offset] [count]
"""
import struct, sys


def rva_to_off(data, sections, rva):
    for va, vsz, raw, rsz in sections:
        if va <= rva < va + max(vsz, rsz):
            return raw + (rva - va)
    return None


def parse_pe(data):
    pe = struct.unpack_from('<I', data, 0x3C)[0]
    assert data[pe:pe + 4] == b'PE\x00\x00', 'not PE'
    coff = pe + 4
    nsec = struct.unpack_from('<H', data, coff + 2)[0]
    optsz = struct.unpack_from('<H', data, coff + 16)[0]
    opt = coff + 20
    magic = struct.unpack_from('<H', data, opt)[0]
    if magic == 0x10B:
        dd = opt + 0x60
    else:
        dd = opt + 0x70
    cli_rva, cli_sz = struct.unpack_from('<II', data, dd + 14 * 8)
    secs = []
    so = opt + optsz
    for i in range(nsec):
        e = so + i * 40
        vsz, va, rsz, raw = struct.unpack_from('<IIII', data, e + 8)
        secs.append((va, vsz, raw, rsz))
    return rva_to_off(data, secs, cli_rva)


def parse_metadata(data, cli_off):
    md_rva, md_sz = struct.unpack_from('<II', data, cli_off + 8)
    # need sections again
    # reuse: recompute
    pe = struct.unpack_from('<I', data, 0x3C)[0]
    coff = pe + 4
    nsec = struct.unpack_from('<H', data, coff + 2)[0]
    optsz = struct.unpack_from('<H', data, coff + 16)[0]
    opt = coff + 20
    magic = struct.unpack_from('<H', data, opt)[0]
    dd = opt + (0x60 if magic == 0x10B else 0x70)
    secs = []
    so = opt + optsz
    for i in range(nsec):
        e = so + i * 40
        vsz, va, rsz, raw = struct.unpack_from('<IIII', data, e + 8)
        secs.append((va, vsz, raw, rsz))
    md = rva_to_off(data, secs, md_rva)
    assert data[md:md + 4] == b'BSJB', 'no BSJB @%d' % md
    verlen = struct.unpack_from('<I', data, md + 12)[0]
    p = md + 16 + verlen
    p += 2 + 2  # flags, streams
    nstreams = struct.unpack_from('<H', data, md + 16 + verlen + 2)[0]
    streams = {}
    for i in range(nstreams):
        off, size = struct.unpack_from('<II', data, p)
        p += 8
        name = b''
        while data[p] != 0:
            name += data[p:p + 1]
            p += 1
        p += 1
        while (p - md) % 4 != 0:
            p += 1
        streams[name.decode()] = (md + off, size)
    return streams


def walk_us(data, off, size):
    """Yield (offset, text) for each string in the #US heap."""
    p = off + 1  # first byte is 0x00
    end = off + size
    out = []
    while p < end:
        b0 = data[p]
        if b0 == 0:
            p += 1
            continue
        if (b0 & 0x80) == 0:
            ln = b0
            p += 1
        elif (b0 & 0xC0) == 0x80:
            ln = ((b0 & 0x3F) << 8) | data[p + 1]
            p += 2
        elif (b0 & 0xE0) == 0xC0:
            ln = ((b0 & 0x1F) << 24) | (data[p + 1] << 16) | (data[p + 2] << 8) | data[p + 3]
            p += 4
        else:
            p += 1
            continue
        if ln == 0 or p + ln > end:
            p += 1
            continue
        raw = data[p:p + ln - 1]
        p += ln  # includes the 1-byte flag
        try:
            t = raw.decode('utf-16-le')
        except Exception:
            t = raw.decode('utf-16-le', 'replace')
        out.append((p - ln, t))
    return out


if __name__ == '__main__':
    path = sys.argv[1]
    data = open(path, 'rb').read()
    cli = parse_pe(data)
    streams = parse_metadata(data, cli)
    print('streams:', {k: v for k, v in streams.items()})
    us_off, us_size = streams['#US']
    items = walk_us(data, us_off, us_size)
    print('#US strings:', len(items), 'off=%d size=%d' % (us_off, us_size))
    if len(sys.argv) > 2:
        start = int(sys.argv[2], 0)
        cnt = int(sys.argv[3]) if len(sys.argv) > 3 else 60
        idx = min(range(len(items)), key=lambda i: abs(items[i][0] - start))
        for o, t in items[idx:idx + cnt]:
            print('%8d %r' % (o, t))
    else:
        # save all
        import json
        json.dump(items, open(path + '.us.json', 'w', encoding='utf-8'), ensure_ascii=False)
        print('saved ->', path + '.us.json')
