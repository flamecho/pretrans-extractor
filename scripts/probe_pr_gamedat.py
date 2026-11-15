#!/usr/bin/env python3
# Scan EVERY game.dat LIBP entry (decrypted) for Malie VM script markers.
import os, struct, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import malie_extract as M

GD = os.path.join(VNTRANS_HOME, "_work_psychicrain/src/psychic_rain/data/game.dat")
gd = open(GD,"rb").read()
k = M.detect_key(gd[:64]); sig, entries = M.read_libp(gd, k)
print("game.dat key=%d files=%d"%(k,len(entries)))

markers = [b"maliescenario", b"_ms_message", b"MALIE_NAME", b"LIBP", b"LIBU", b"MZ"]
def u16(b,o): return struct.unpack_from("<H",b,o)[0]
def u32(b,o): return struct.unpack_from("<I",b,o)[0]
# nested LIBP scan inside an entry
def scan_nested(d, depth=0):
    res=[]
    for kk in range(len(M.KEYS)):
        try:
            h=M.read_decrypt(d,kk,0,16)
        except: continue
        if h[:4] in (b"LIBP",b"LIBU"):
            try:
                s2,en=M.read_libp(d,kk)
                res.append(("LIBP-in-LIBP key=%d files=%d"%(kk,len(en)), en))
            except Exception as e:
                res.append(("LIBP-in-LIBP key=%d parse-err %r"%(kk,e), []))
    return res

hits=[]
for f,o,l in entries:
    if l < 64: continue
    data = M.read_decrypt(gd, k, o, l) if k!=-1 else gd[o:o+l]
    found=[]
    for m in markers:
        c=data.count(m)
        if c: found.append((m.decode("latin1"),c))
    if found:
        hits.append((f,o,l,found))
        print(f"\n### {f}  off={hex(o)} size={l}")
        for mn,c in found: print(f"     {mn}: {c}")
        # if malie scenario inside, try parse
        if any(x[0]=="maliescenario" for x in found):
            try:
                P=M.parse_exec(data); msgs,_=M.walk_script(P,"沙耶")
                print(f"     PARSE OK msgs={len(msgs)}  sample:", msgs[0][:60] if msgs else "")
            except Exception as e:
                print("     parse-err", repr(e)[:60])
        # nested libp?
        for desc,en in scan_nested(data):
            print("     nested:", desc, "->", [(x[0],x[2]) for x in en[:5]])

print("\n=== SUMMARY: entries with Malie/LIBP markers ===", len(hits))
if not hits:
    print("NONE. No scenario in game.dat. Largest 8 entries:")
    for f,o,l in sorted(entries,key=lambda x:-x[2])[:8]:
        print(f"   {l:>10} {f}")
