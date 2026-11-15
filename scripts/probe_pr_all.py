#!/usr/bin/env python3
# Dump ALL PE resource entries + all LIBP entries; flag scenario-like ones.
import os, struct, zlib, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import malie_extract as M

EXE = os.path.join(VNTRANS_HOME, "_work_psychicrain/src/psychic_rain/psychic_rain.exe")
d = open(EXE,"rb").read()
e_lfanew = struct.unpack_from("<I",d,0x3c)[0]
opt = d[e_lfanew+24]; ns = struct.unpack_from("<H",d,e_lfanew+6)[0]
soh = struct.unpack_from("<H",d,e_lfanew+20)[0]; sh = e_lfanew+24+soh
secs=[]
for i in range(ns):
    b=sh+i*40
    secs.append((d[b:b+8].split(b"\x00")[0],struct.unpack_from("<I",d,b+8)[0],
                 struct.unpack_from("<I",d,b+12)[0],struct.unpack_from("<I",d,b+16)[0],
                 struct.unpack_from("<I",d,b+20)[0]))
def rva2off(rva):
    for nm,vsize,vrva,rawsize,rawoff in secs:
        if vrva<=rva<vrva+vsize: return rawoff+(rva-vrva)
    return None
resrva = struct.unpack_from("<I",d,e_lfanew+24+(96 if opt==0x10b else 112))[0]
base_off = rva2off(resrva)
def get_name(off):
    p=base_off+off; l=struct.unpack_from("<H",d,p)[0]
    return d[p+2:p+2+l*2].decode("utf-16-le","replace")
found=[]
def walk(entry_off, path):
    ent=base_off+entry_off
    nc=struct.unpack_from("<H",d,ent+12)[0]; ic=struct.unpack_from("<H",d,ent+14)[0]
    children=ent+16
    for i in range(nc+ic):
        co=children+i*8
        nid=struct.unpack_from("<I",d,co)[0]; dto=struct.unpack_from("<I",d,co+4)[0]
        nm=get_name(nid&0x7fffffff) if (nid&0x80000000) else str(nid)
        if dto&0x80000000: walk(dto&0x7fffffff, path+[nm])
        else:
            de=base_off+dto; rva=struct.unpack_from("<I",d,de)[0]; size=struct.unpack_from("<I",d,de+4)[0]
            found.append((path+[nm], rva2off(rva), size))
walk(0,[])
print("=== ALL %d resource entries ==="%len(found))
for pth,off,size in found:
    data=d[off:off+min(size,24)]
    flag=""
    try:
        zlib.decompress(d[off:off+size]); flag="[ZLIB-OK]"
    except: pass
    if any(k in "/".join(pth).upper() for k in ("MALIE","SCEN","EXEC","SCRIPT","MSG","TEXT","DATA")):
        flag+="[SCEN-LIKE]"
    print(f"  {pth}  off={hex(off)} size={size} {flag} head={data.hex()}")

print("\n=== LIBP entries across data/*.dat ===")
SRC=os.path.join(os.path.dirname(EXE),"data")
for fn in ("game.dat","movie.dat","sound.dat","voice.dat"):
    p=os.path.join(SRC,fn)
    if not os.path.exists(p): continue
    dd=open(p,"rb").read(); k=M.detect_key(dd[:64])
    if k is None: print(f"  {fn}: no LIBP key"); continue
    sig,entries=M.read_libp(dd,k)
    hits=[(f,o,l) for f,o,l in entries if any(t in f.lower() for t in ("exec","scen","script","scn",".ks",".tbl",".mes",".txt",".spt","malie"))]
    print(f"  {fn}: key={k} files={len(entries)} scen-like={len(hits)}")
    for f,o,l in hits[:30]: print(f"      {l:>10} {f}")
