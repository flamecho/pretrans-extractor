#!/usr/bin/env python3
"""LSDARC V.100 (Takuyo gss engine) reader.
Index = magic[12] "LSDARC V.100" + u32 count + count x {u32 isPacked, u32 offset,
u32 unpackedSize, u32 size, name\0}.
"""
import struct, sys, os, zlib

MAGIC = b"LSDARC V.100"

def read_index(path):
    d = open(path, "rb").read()
    assert d[:12] == MAGIC, d[:12]
    count = struct.unpack_from("<I", d, 12)[0]
    off = 16
    entries = []
    for i in range(count):
        isp, ofs, usz, sz = struct.unpack_from("<IIII", d, off)
        off += 16
        e = d.index(b"\0", off)
        name = d[off:e].decode("cp932", "replace")
        off = e + 1
        entries.append(dict(idx=i, isp=isp, off=ofs, usz=usz, sz=sz, name=name))
    return entries, off

def dump_arc(arcpath, entries, outdir):
    d = open(arcpath, "rb").read()
    os.makedirs(outdir, exist_ok=True)
    for e in entries:
        blob = d[e["off"]:e["off"] + e["sz"]]
        e["_blob"] = blob
    return d

if __name__ == "__main__":
    for name in ["SCRDATA", "SYSDATA", "BMPDATA", "FONTDATA", "WAVDATA"]:
        binp = f"dec/DATA/{name}.BIN"
        if not os.path.exists(binp):
            continue
        entries, end = read_index(binp)
        n_isp = sum(1 for e in entries if e["isp"])
        print(f"=== {name}: count={len(entries)} packed={n_isp} indexEnd=0x{end:x}")
        for e in entries[:8]:
            print(f"  {e['idx']:4d} isp={e['isp']} off=0x{e['off']:x} usz=0x{e['usz']:x} sz=0x{e['sz']:x} {e['name']}")
