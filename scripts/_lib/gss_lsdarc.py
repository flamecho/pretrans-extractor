#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LSDARC V.100 container (Takuyo gss).  Index = "<NAME>.BIN", data = "<NAME>.ARC".

Index layout:
    magic[12] "LSDARC V.100" | u32 count |
    count x { u32 isPacked, u32 offset, u32 unpackedSize, u32 size, name\\0 }

Packed entries are decoded with gss_codec (LSD\\x1a header at entry offset).
"""
import os
import struct
from _lib import gss_codec as C

MAGIC = b"LSDARC V.100"


def read_index(bin_path):
    d = open(bin_path, "rb").read()
    assert d[:12] == MAGIC, d[:12]
    count = struct.unpack_from("<I", d, 12)[0]
    off = 16
    ents = []
    for i in range(count):
        isp, ofs, usz, sz = struct.unpack_from("<IIII", d, off)
        off += 16
        e = d.index(b"\0", off)
        name = d[off:e].decode("cp932", "replace")
        off = e + 1
        ents.append(dict(idx=i, isp=bool(isp), off=ofs, usz=usz, sz=sz, name=name))
    return ents, off


def load(bin_path, arc_path):
    ents, _ = read_index(bin_path)
    arc = open(arc_path, "rb").read()
    return ents, arc


def unpack_entry(arc, e):
    """Return the decoded file bytes for one index entry."""
    if not e["isp"]:
        return arc[e["off"]:e["off"] + e["usz"]]
    ofs, usz, sz = e["off"], e["usz"], e["sz"]
    enc = chr(arc[ofs + 4])
    pack = chr(arc[ofs + 5])
    payload = arc[ofs + 12:ofs + sz]
    bp = bytes(payload) + b"\x00" * 16
    if pack == "H":
        out = C.unpack_h(bp, usz)
    elif pack == "D":
        out = C.unpack_d(bp, usz)
    elif pack == "R":
        out = C.unpack_r(payload, usz)
    else:
        out = arc[ofs + 12:ofs + 12 + usz]
    return C.decrypt(out, enc)[:usz]


def unpack_all(bin_path, arc_path):
    ents, arc = load(bin_path, arc_path)
    return {e["name"]: unpack_entry(arc, e) for e in ents}
