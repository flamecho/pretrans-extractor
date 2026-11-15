#!/usr/bin/env python3
# Check completeness: VIRTUALFILESYSTEM table, voice.dat format, large game.dat entries.
import os, struct, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import malie_extract as M

EXE = os.path.join(VNTRANS_HOME, "_work_psychicrain/src/psychic_rain/psychic_rain.exe")
SRC = os.path.join(VNTRANS_HOME, "_work_psychicrain/src/psychic_rain")
d = open(EXE,"rb").read()
e_lfanew = struct.unpack_from("<I",d,0x3c)[0]; opt=d[e_lfanew+24]; ns=struct.unpack_from("<H",d,e_lfanew+6)[0]
soh=struct.unpack_from("<H",d,e_lfanew+20)[0]; sh=e_lfanew+24+soh
secs=[]
for i in range(ns):
    b=sh+i*40
    secs.append((d[b:b+8].split(b"\x00")[0],struct.unpack_from("<I",d,b+8)[0],struct.unpack_from("<I",d,b+12)[0],struct.unpack_from("<I",d,b+16)[0],struct.unpack_from("<I",d,b+20)[0]))
def rva2off(rva):
    for nm,vsize,vrva,rawsize,rawoff in secs:
        if vrva<=rva<vrva+vsize: return rawoff+(rva-vrva)
    return None
resrva=struct.unpack_from("<I",d,e_lfanew+24+(96 if opt==0x10b else 112))[0]
base_off=rva2off(resrva)
def get_name(o):
    p=base_off+o; l=struct.unpack_from("<H",d,p)[0]; return d[p+2:p+2+l*2].decode("utf-16-le","replace")
found=[]
def walk(eo,path):
    ent=base_off+eo; nc=struct.unpack_from("<H",d,ent+12)[0]; ic=struct.unpack_from("<H",d,ent+14)[0]; ch=ent+16
    for i in range(nc+ic):
        co=ch+i*8; nid=struct.unpack_from("<I",d,co)[0]; dto=struct.unpack_from("<I",d,co+4)[0]
        nm=get_name(nid&0x7fffffff) if (nid&0x80000000) else str(nid)
        if dto&0x80000000: walk(dto&0x7fffffff,path+[nm])
        else:
            de=base_off+dto; rva=struct.unpack_from("<I",d,de)[0]; sz=struct.unpack_from("<I",d,de+4)[0]
            found.append((path+[nm],rva2off(rva),sz))
walk(0,[])
vf=[(p,o,s) for p,o,s in found if "VIRTUAL" in "/".join(p).upper() or "MALIE_PROTECT" in "/".join(p).upper()]
print("=== VIRTUALFILESYSTEM / MALIE_PROTECT resources ===")
for p,o,s in vf:
    print(f"[{'/'.join(p)}] off={hex(o)} size={s}")
    print("   raw:", d[o:o+s].hex())
    # try decode as utf-16
    print("   u16:", d[o:o+s].decode("utf-16-le","replace"))

print("\n=== voice.dat format check ===")
vd=open(os.path.join(SRC,"data","voice.dat"),"rb").read()
print("  size", len(vd), "head:", vd[:32].hex())
for k in range(len(M.KEYS)):
    h=M.read_decrypt(vd,k,0,16)
    if h[:4] in (b"LIBP",b"LIBU"): print("  LIBP key",k,"->",h[:4]); break
else:
    print("  no LIBP key matched")
# try parse as raw exec.dat
try:
    P=M.parse_exec(vd); print("  voice.dat parses as exec: FUNCS",len(P["FUNCS"]),"msgs via walk:",len(M.walk_script(P,"沙耶")[0]))
except Exception as e: print("  voice.dat not exec:", repr(e)[:80])

print("\n=== game.dat entries > 100KB that are NOT picture/ogg/csv/svg ===")
gd=open(os.path.join(SRC,"data","game.dat"),"rb").read(); k=M.detect_key(gd[:64])
sig,entries=M.read_libp(gd,k)
big=[(f,o,l) for f,o,l in entries if l>100000 and not any(x in f.lower() for x in ("picture","ogg","csv","svg",".png",".mpg",".jpg"))]
print("  count big non-gfx:", len(big))
for f,o,l in sorted(big,key=lambda x:-x[2])[:30]: print(f"    {l:>10} {f}")
# also: any entry whose name contains exec/scenario/script
sc=[(f,o,l) for f,o,l in entries if any(t in f.lower() for t in ("exec","scen","script",".ks",".dat",".tbl",".mes"))]
print("  scen-name:", len(sc))
for f,o,l in sc[:30]: print(f"    {l:>10} {f}")
