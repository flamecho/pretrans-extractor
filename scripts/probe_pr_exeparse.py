#!/usr/bin/env python3
# Test: is the EXEC resource a parseable Malie VM script (real Psychic Rain scenario)?
import os, struct, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import malie_extract as M

EXE = os.path.join(VNTRANS_HOME, "_work_psychicrain/src/psychic_rain/psychic_rain.exe")
OUT = os.path.join(VNTRANS_HOME, "_work_psychicrain/maliescenario_raw.bin")
d = open(EXE,"rb").read()
# re-derive EXEC resource offset (0x1b5e20, size 364797) from earlier probe
off=0x1b5e20; size=364797
raw = d[off:off+size]
open(OUT,"wb").write(raw)
print("EXEC resource size", size)
print("head 64:", raw[:64].hex())
# try parse_exec
try:
    P = M.parse_exec(raw)
    FUNCS=P["FUNCS"]
    print("parse_exec OK: FUNCS=",len(FUNCS))
    print("  func names:", [n for n,_,_ in FUNCS][:20])
    # walk
    msgs,_ = M.walk_script(P, "沙耶")
    print("  _ms_message count:", len(msgs))
    # search STRT for markers
    strt = P["STRT"]
    for tok in ("沙耶","サイキック","宗像","水鏡","キリト","マリア","クラウス"):
        print(f"    STRT '{tok}':", strt.count(tok.encode("utf-16-le")))
    # sample first 5 messages
    print("  sample msgs:")
    for s in msgs[:5]:
        print("    >>", s[:80].replace("\x00","\\0"))
except Exception as e:
    print("parse_exec FAILED:", repr(e))
    # inspect as possible wrapper: look for inner exec.dat signature after some header
    # search for UTF-16 'maliescenario' inside raw
    print("  contains 'maliescenario'(u16)?", raw.count("maliescenario".encode("utf-16-le")))
    print("  contains LIBP/LIBU?", raw.count(b"LIBP"), raw.count(b"LIBU"))
    print("  first 200 bytes:", raw[:200].hex())
