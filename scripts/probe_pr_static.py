#!/usr/bin/env python3
# Decisive: does the REAL Psychic Rain scenario exist anywhere statically?
import os, struct
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SRC = os.path.join(VNTRANS_HOME, "_work_psychicrain/src")
markers = {
    "_ms_message(asc)": b"_ms_message",
    "maliescenario(asc)": b"maliescenario",
    "_ms_message(u16)": "_ms_message".encode("utf-16-le"),
    "maliescenario(u16)": "maliescenario".encode("utf-16-le"),
    "サイキック(u16)": "サイキック".encode("utf-16-le"),
    "沙耶(u16)": "沙耶".encode("utf-16-le"),
    "サイキック・レインボー(u16)": "サイキック・レインボー".encode("utf-16-le"),
    "LIBP(asc)": b"LIBP",
    "LIBU(asc)": b"LIBU",
}
hits = {}
for root,_,files in os.walk(SRC):
    for fn in files:
        p=os.path.join(root,fn)
        try: d=open(p,"rb").read()
        except: continue
        rel=os.path.relpath(p,SRC)
        for name,m in markers.items():
            c=d.count(m)
            if c:
                hits.setdefault(rel,{})[name]=c
print("=== marker hits per file ===")
for rel in sorted(hits):
    print(f"\n[{rel}] size={os.path.getsize(os.path.join(SRC,rel))}")
    for name,c in sorted(hits[rel].items(), key=lambda x:-x[1]):
        print(f"   {name}: {c}")
