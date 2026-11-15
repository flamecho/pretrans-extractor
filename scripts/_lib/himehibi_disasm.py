#!/usr/bin/env python3
"""SCR 2.00 (Takuyo gss / LSDARC) disassembler with auto-calibrated operand sizes."""
import struct, sys, os, collections

# type -> size in bytes (None = string, NUL terminated)
SIZES = {0x00: 1, 0x01: 4, 0x02: 2, 0x03: None, 0x04: 2, 0x05: 4, 0x06: 2, 0x07: 2, 0x08: 2}

def disasm(b, start=16, sizes=None):
    sizes = sizes or SIZES
    i, n = start, len(b)
    out = []
    while i + 3 <= n:
        op = struct.unpack_from("<H", b, i)[0]
        size = b[i + 2]
        if size < 5 or i + size > n:
            return out, (i, "sizebad", size)
        ident = struct.unpack_from("<H", b, i + 3)[0]
        p = i + 5
        ops = []
        while p < i + size:
            t = b[p]; p += 1
            if t == 0x03:
                e = b.find(b"\x00", p, i + size + 1)
                if e < 0 or e > i + size:
                    return out, (i, "str", t)
                ops.append((3, b[p:e].decode("cp932", "replace"))); p = e + 1
            else:
                sz = sizes.get(t)
                if sz is None:
                    return out, (i, f"type{t:#x}", t)
                if p + sz > i + size:
                    return out, (i, "ovf", t)
                ops.append((t, b[p:p + sz].hex())); p += sz
        if p != i + size:
            return out, (i, "misalign", f"p={p-i} sz={size}")
        out.append((i, op, size, ident, ops))
        i += size
    return out, None

def load():
    from _lib.himehibi_lsdarc import read_index
    ents, _ = read_index("dec/DATA/SCRDATA.BIN")
    d = open("dec/DATA/SCRDATA.ARC", "rb").read()
    return ents, {e["name"]: d[e["off"]:e["off"] + e["usz"]] for e in ents}
