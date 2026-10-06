#!/usr/bin/env python3
"""PSARC (Sony) extractor — big-endian classic PSARC.
Ported from Kuriimu2 plugin_sony/Archives/PSARC (PSARC.cs + PsarcSupport.cs).

Header (BE, 0x20):
  magic[4]=PSAR/PSARC, u16 major, u16 minor, compression[4] ('zlib' or 0),
  u32 tocSize, u32 tocEntrySize, u32 tocEntryCount, u32 blockSize, u32 flags
TocEntry (tocEntrySize bytes):
  md5[16], i32 firstBlockIndex, u40 uncompressedSize, u40 offset
Block table: (tocSize - 0x20 - count*entrySize)/2 entries of u16 BE;
  size==0 -> blockSize; data starts at tocSize.
Blocks whose 2 first bytes == 78DA are zlib; else stored raw (blockSize).
"""
import sys, os, struct, zlib

def parse_names(blob):
    names = []
    cur = bytearray()
    i = 0
    while i < len(blob):
        b = blob[i]
        if b == 0 or b == 10:
            names.append(cur.decode('utf-8', 'replace'))
            cur = bytearray()
        else:
            cur.append(b)
        i += 1
    if cur:
        names.append(cur.decode('utf-8', 'replace'))
    return names

def decompress_entry(data, blocks, first_index, block_size, out_size):
    nblocks = (out_size + block_size - 1) // block_size
    out = bytearray()
    for k in range(nblocks):
        off, size = blocks[first_index + k]
        raw = data[off:off + size]
        if len(raw) >= 2 and raw[0] == 0x78 and raw[1] in (0xDA, 0x9C, 0x01):
            out += zlib.decompress(raw)
        else:
            out += raw
    return bytes(out[:out_size])

def main(path, outdir):
    data = open(path, 'rb').read()
    magic = data[0:4]
    major, minor = struct.unpack('>HH', data[4:8])
    comp = data[8:12]
    tocSize, tocEntrySize, tocEntryCount, blockSize, flags = struct.unpack('>IIIII', data[12:32])
    print(f"magic={magic} v{major}.{minor} comp={comp} tocSize={tocSize} "
          f"entrySize={tocEntrySize} count={tocEntryCount} blockSize={blockSize} flags={flags}")
    off = 32
    entries = []
    for i in range(tocEntryCount):
        md5 = data[off:off + 16]
        first_block = struct.unpack('>i', data[off + 16:off + 20])[0]
        us = int.from_bytes(data[off + 20:off + 25], 'big')
        uo = int.from_bytes(data[off + 25:off + 30], 'big')
        entries.append((first_block, us, uo))
        off += tocEntrySize
    blockCount = (tocSize - off) // 2
    sizes = struct.unpack('>%dH' % blockCount, data[off:off + blockCount * 2])
    boff = tocSize
    blocks = []
    for s in sizes:
        sz = blockSize if s == 0 else s
        blocks.append((boff, sz))
        boff += sz
    print(f"blocks={blockCount} dataEnd={boff} fileSize={len(data)}")

    # entry0 = names table
    fb, us, uo = entries[0]
    names_blob = decompress_entry(data, blocks, fb, blockSize, us)
    names = parse_names(names_blob)
    print(f"names={len(names)} entries={tocEntryCount-1}")
    if outdir:
        os.makedirs(outdir, exist_ok=True)
    total = 0
    for i in range(1, tocEntryCount):
        fb, us, uo = entries[i]
        blob = decompress_entry(data, blocks, fb, blockSize, us)
        nm = names[i - 1] if i - 1 < len(names) else f"{i:08d}.bin"
        nm = nm.replace('\\', '/').lstrip('/')
        dst = os.path.join(outdir, nm) if outdir else None
        if dst:
            d = os.path.dirname(dst)
            if d:
                os.makedirs(d, exist_ok=True)
            with open(dst, 'wb') as f:
                f.write(blob)
        total += len(blob)
        if i <= 30 or i % 200 == 0:
            print(f"  [{i:4d}] {nm}  {len(blob)} B")
    print(f"extracted {tocEntryCount-1} files, {total} bytes -> {outdir}")

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
