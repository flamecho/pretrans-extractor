#!/usr/bin/env python3
# Focused probe: where is the REAL Psychic Rain scenario?
import os, struct, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import malie_extract as M

SRC = os.path.join(VNTRANS_HOME, "_work_psychicrain/src/psychic_rain")

def scan_markers(path):
    d = open(path, "rb").read()
    n = len(d)
    res = {}
    for m in (b"MalieScenario", b"LIBP", b"LIBU", b"2JEV",
              b"ZLibIn_Full", b"maliesetup", b"exec.dat", b"psychic"):
        res[m.decode("latin1")] = d.count(m)
    # zlib magic (deflate)
    zl = 0
    i = 0
    while True:
        j = d.find(b"\x78", i)
        if j < 0: break
        if j+1 < n and d[j+1] in (0x01,0x9c,0xda):
            zl += 1
        i = j+1
        if i > n-2: break
    res["zlib_magic(78 01/9c/da)"] = zl
    # high-entropy section heuristic: ratio of bytes with high shannon
    return res, n

print("=== SOURCE FILE SCAN ===")
for fn in sorted(os.listdir(SRC)):
    p = os.path.join(SRC, fn)
    if os.path.isfile(p):
        r, n = scan_markers(p)
        print(f"\n[{fn}] size={n}")
        for k,v in r.items():
            if v: print(f"   {k}: {v}")

print("\n=== data/*.dat as LIBP ? ===")
for fn in ("game.dat","movie.dat","sound.dat","voice.dat"):
    p = os.path.join(SRC, "data", fn)
    if not os.path.exists(p):
        print(f"  {fn}: missing"); continue
    d = open(p,"rb").read()
    k = M.detect_key(d[:64])
    print(f"  {fn}: size={len(d)} camellia_key={k}")
    if k is not None:
        try:
            sig, entries = M.read_libp(d, k)
            print(f"      sig={sig} files={len(entries)}")
            for f,o,l in entries[:20]:
                print(f"        {l:>10}  {f}")
        except Exception as e:
            print(f"      read_libp err: {e!r}")
