import struct, sys, collections, os, json

def parse_container(path):
    d = open(path, 'rb').read()
    cnt, bc_off, bc_size, z = struct.unpack_from('<4I', d, 0)
    ents = []
    off = 0x10
    while off + 64 <= bc_off:
        nm = d[off:off+48].split(b'\0')[0].decode('cp932', 'replace')
        a, o, s, i = struct.unpack_from('<4I', d, off+48)
        if not nm:
            break
        ents.append((nm, a, o, s, i))
        off += 64
    return d, cnt, bc_off, bc_size, ents

def walk(bc):
    """yield (off, op, payload)"""
    off = 0
    n = len(bc)
    while off + 4 <= n:
        op, ln = struct.unpack_from('<HH', bc, off)
        if ln < 4 or off + ln > n:
            yield (off, op, ln, None)
            return
        yield (off, op, ln, bc[off+4:off+ln])
        off += ln

if __name__ == '__main__':
    path = sys.argv[1]
    d, cnt, bc_off, bc_size, ents = parse_container(path)
    print('file', path, 'size', len(d))
    print('hdr cnt=%d bcOff=0x%x bcSize=0x%x' % (cnt, bc_off, bc_size))
    print('entries', len(ents))
    for e in ents[:6]:
        print('  ', e)
    bc = d[bc_off:bc_off+bc_size]
    ops = collections.Counter()
    samples = {}
    bad = 0
    for (o, op, ln, pl) in walk(bc):
        ops[op] += 1
        if pl is None:
            bad += 1
            break
        if op not in samples:
            samples[op] = (o, ln, pl[:64])
    print('opcodes:', len(ops), 'bad', bad)
    for op, c in ops.most_common(40):
        s = samples[op]
        print('  op=0x%04x n=%d len=%d %s' % (op, c, s[1], s[2].hex(' ')))
