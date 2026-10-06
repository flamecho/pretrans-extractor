#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from himehibi_lsdarc import read_index

def load_scripts():
    ents, _ = read_index("dec/DATA/SCRDATA.BIN")
    d = open("dec/DATA/SCRDATA.ARC", "rb").read()
    out = {}
    for e in ents:
        out[e["name"]] = d[e["off"]:e["off"] + e["usz"]]
    return ents, out

def scan_strings(b, ctx=10):
    out = []
    i = 0
    n = len(b)
    while i < n - 1:
        if b[i] == 0x03:
            # find NUL within next 300 bytes
            end = b.find(b"\x00", i + 1, min(n, i + 300))
            if end > 0:
                s = b[i + 1:end]
                try:
                    t = s.decode("cp932")
                    if all(ord(c) >= 0x20 for c in t) and len(s) >= 2:
                        out.append((i, b[max(0, i - ctx):i], t))
                        i = end + 1
                        continue
                except Exception:
                    pass
        i += 1
    return out

if __name__ == "__main__":
    ents, scripts = load_scripts()
    name = sys.argv[1] if len(sys.argv) > 1 else "COM06_30_01"
    b = scripts[name]
    print("=== ", name, "len", len(b))
    print("header:", b[:16].hex())
    for off, pre, t in scan_strings(b):
        # length of string bytes incl NUL
        raw = b[off + 1:off + 1 + len(t.encode("cp932")) + 1]
        print(f"@{off:6d} pre={pre.hex():20s} L={len(t.encode('cp932'))+1:3d} {t!r}")
