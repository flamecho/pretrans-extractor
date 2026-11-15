#!/usr/bin/env python3
import os, struct, re, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import malie_extract as M

EXE = os.path.join(VNTRANS_HOME, "_work_psychicrain/src/psychic_rain/psychic_rain.exe")
d = open(EXE,"rb").read()
off=0x1b5e20; size=364797
raw = d[off:off+size]
P = M.parse_exec(raw)
VM_DATA=P["VM_DATA"]; STRT=P["STRT"]; VM_CODE=P["VM_CODE"]
# scan STRT + VM_DATA for ascii path-like / filename strings
for region_name, region in (("STRT",STRT),("VM_DATA",VM_DATA)):
    # ascii printable runs >=4
    runs = re.findall(rb'[\x20-\x7e]{4,}', region)
    paths=[r.decode("latin1") for r in runs if (b'/' in r or b'.dat' in r or b'exec' in r.lower() or b'scen' in r.lower() or b'.ks' in r.lower())]
    print(f"=== {region_name}: path-like strings ({len(paths)}) ===")
    for p in paths[:40]:
        print("   ", p)
# also: does the script call a scenario-load? search VM_CODE for string-arg ops referencing filenames
# count _ms_message and total string-table usage
NAME2ID={n:i for n,i,c in P["FUNCS"]}
print("\nFUNCS of interest:", [n for n,_,_ in P["FUNCS"] if any(k in n for k in ("System_Goto","Call","Load","Scenario","scenario","Include","Exec"))])
# Check STRT for any dialogue that looks like a route/title divider
strt_dec = STRT.decode("utf-16-le","replace")
for kw in ("章","プロローグ","エピローグ","ＥＮＤ","終","ルート","第",":","："):
    print(f"  STRT contains {kw!r}: {kw in strt_dec}")
