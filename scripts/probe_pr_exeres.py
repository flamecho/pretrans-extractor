#!/usr/bin/env python3
# Parse PE .rsrc of psychic_rain.exe, dump MalieScenario resource, test zlib.
import os, struct, zlib, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
from collections import Counter

EXE = os.path.join(VNTRANS_HOME, "_work_psychicrain/src/psychic_rain/psychic_rain.exe")
OUT = os.path.join(VNTRANS_HOME, "_work_psychicrain/maliescenario_raw.bin")

d = open(EXE,"rb").read()
e_lfanew = struct.unpack_from("<I",d,0x3c)[0]
opt = d[e_lfanew+24]
ns = struct.unpack_from("<H",d,e_lfanew+6)[0]
soh = struct.unpack_from("<H",d,e_lfanew+20)[0]
sh = e_lfanew+24+soh
secs=[]
for i in range(ns):
    b=sh+i*40
    secs.append((d[b:b+8].split(b"\x00")[0],
                 struct.unpack_from("<I",d,b+8)[0],
                 struct.unpack_from("<I",d,b+12)[0],
                 struct.unpack_from("<I",d,b+16)[0],
                 struct.unpack_from("<I",d,b+20)[0]))
def rva2off(rva):
    for nm,vsize,vrva,rawsize,rawoff in secs:
        if vrva<=rva<vrva+vsize:
            return rawoff+(rva-vrva)
    return None
resrva = struct.unpack_from("<I",d,e_lfanew+24+(96 if opt==0x10b else 112))[0]
base_off = rva2off(resrva)
print("RESOURCE section base_off", hex(base_off), "resrva", hex(resrva))

def get_name(off):
    p = base_off+off
    l = struct.unpack_from("<H",d,p)[0]
    return d[p+2:p+2+l*2].decode("utf-16-le","replace")

found=[]
def walk(entry_off, path):
    ent = base_off+entry_off
    nc=struct.unpack_from("<H",d,ent+12)[0]; ic=struct.unpack_from("<H",d,ent+14)[0]
    children=ent+16
    for i in range(nc+ic):
        co=children+i*8
        nid=struct.unpack_from("<I",d,co)[0]; dto=struct.unpack_from("<I",d,co+4)[0]
        nm = get_name(nid&0x7fffffff) if (nid&0x80000000) else str(nid)
        if dto&0x80000000:
            walk(dto&0x7fffffff, path+[nm])
        else:
            de=base_off+dto
            rva=struct.unpack_from("<I",d,de)[0]; size=struct.unpack_from("<I",d,de+4)[0]
            found.append((path+[nm], rva2off(rva), size))

walk(0, [])
print("\n=== total resource leaf entries:", len(found))
for pth, off, size in found:
    joined="/".join(pth)
    if not any(k in joined for k in ("Malie","EXEC","SCEN","exec")): continue
    data=d[off:off+size]
    print(f"\n### {pth}  off={hex(off)} size={size}")
    print("  first32:", data[:32].hex())
    try:
        dec=zlib.decompress(data)
        print(f"  ZLIB OK -> {len(dec)} bytes; first32:", dec[:32].hex())
        open(OUT,"wb").write(dec)
        print("  wrote", OUT)
    except Exception as e:
        print("  zlib fail:", e)
        uniq=len(set(data[:8192]))
        print(f"  entropy sample: {uniq} unique/8192 bytes (high => likely encrypted)")
