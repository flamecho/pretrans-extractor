#!/usr/bin/env python3
"""ROM2 archiver (Kalmia8 / 鳥籠のマリアージュ PSV).

Format (reverse-engineered):
  header 0x20 bytes:
    0x00 magic "ROM2"
    0x04 u32 version (1)
    0x08 u32 ? (metadata end-ish)
    0x0c u32 unit (0x200) -- file offsets are in units of this
    0x10 16B digest
  then a sequence of directory blocks (each 16-byte aligned):
    u32 count                      (includes "." and "..")
    count * 12B entry:
        u32 f0 : name offset relative to block start (|= 0x80000000 for dir)
        u32 f1 : file offset in units of `unit`  (files only)
        u32 f2 : file size in bytes              (files only)
    count NUL-terminated name strings (at block_start + (f0 & 0x7fffffff))

Directory blocks are laid out sequentially; nesting is implicit (BFS order not
guaranteed -> we resolve the tree by matching dir-entry names to blocks in file
order, children queued in entry order).
"""
import struct, os, sys

def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]

def parse_blocks(d):
    N = len(d)
    pos = 0x20
    blocks = []
    while pos + 4 <= N:
        cnt = u32(d, pos)
        if cnt == 0 or cnt > 20000:
            break
        entries = []
        me = 0
        bad = False
        for i in range(cnt):
            eo = pos + 4 + i * 12
            if eo + 12 > N:
                bad = True; break
            f0 = u32(d, eo); f1 = u32(d, eo + 4); f2 = u32(d, eo + 8)
            noff = f0 & 0x7fffffff
            o = pos + noff
            if o >= N:
                bad = True; break
            end = d.find(b'\0', o)
            if end < 0:
                bad = True; break
            nm = d[o:end].decode('latin1')
            entries.append((nm, bool(f0 >> 31), f1, f2))
            me = max(me, end + 1)
        if bad or not entries:
            break
        blocks.append((pos, entries))
        pos = (me + 15) & ~15
    return blocks

def build_tree(blocks):
    from collections import deque
    res = {0: ''}
    queue = deque()
    for (nm, isd, f1, f2) in blocks[0][1]:
        if isd and nm not in ('.', '..'):
            queue.append((nm, ''))
    idx = 1
    while queue and idx < len(blocks):
        nm, parent = queue.popleft()
        p = parent + '/' + nm
        res[idx] = p
        for (cn, cd, cf1, cf2) in blocks[idx][1]:
            if cd and cn not in ('.', '..'):
                queue.append((cn, p))
        idx += 1
    return res

def main():
    src = sys.argv[1]
    outdir = sys.argv[2]
    d = open(src, 'rb').read()
    N = len(d)
    unit = u32(d, 0x0c) or 0x200
    blocks = parse_blocks(d)
    res = build_tree(blocks)
    print('blocks=%d unit=0x%x' % (len(blocks), unit))
    for k in sorted(res):
        print('  block %-3d -> %s' % (k, res[k] or '/'))
    n = 0; total = 0
    for bi, (bpos, entries) in enumerate(blocks):
        base = res.get(bi, '/?block%d' % bi)
        for (nm, isd, f1, f2) in entries:
            if nm in ('.', '..'):
                continue
            if isd:
                continue
            off = f1 * unit
            size = f2
            if off + size > N:
                print('  OOB', base, nm, hex(off), hex(size)); continue
            p = os.path.join(outdir, base.lstrip('/'), nm)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'wb').write(d[off:off + size])
            n += 1; total += size
    print('wrote %d files, %.1f MB' % (n, total / 1048576))

if __name__ == '__main__':
    main()
