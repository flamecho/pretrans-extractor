#!/usr/bin/env python3
# Verify completeness of the EXEC-resource scenario.
import os, struct, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import malie_extract as M

EXE = os.path.join(VNTRANS_HOME, "_work_psychicrain/src/psychic_rain/psychic_rain.exe")
d = open(EXE,"rb").read()
off=0x1b5e20; size=364797
raw = d[off:off+size]
P = M.parse_exec(raw)
FUNCS=P["FUNCS"]; VM_DATA=P["VM_DATA"]; VM_CODE=P["VM_CODE"]; STRT=P["STRT"]
NAME2ID={n:i for n,i,c in FUNCS}
MSG=NAME2ID["_ms_message"]
print("FUNCS=%d  VM_DATA=%d  VM_CODE=%d  STRT=%d  vIdx=%d"%(len(FUNCS),len(VM_DATA),len(VM_CODE),len(STRT),len(P["vIdx"])))
# raw _ms_message call count: scan VM_CODE for op 0x2D with par==MSG
raw_msg=0; pc=0; N=len(VM_CODE)
while pc<N:
    op=VM_CODE[pc]
    if op==0x2D:
        par=struct.unpack_from("<I",VM_CODE,pc+1)[0]
        if par==MSG: raw_msg+=1
        pc+=5
    elif op<=2: pc+=5
    elif op==3: pc+=6
    elif op==4: pc+=3
    elif op in (8,0xD,0x2D): pc+=5
    else: pc+= (M.SKIP_AFTER.get(op,1) if 1<=op<=6 else 1)+1 if False else (1 if op not in (0x33,) else 0)
    if op==0x33: break
print("raw _ms_message opcode count:", raw_msg)
msgs,gs = M.walk_script(P,"沙耶")
print("walk_script outputs:", len(msgs))
# tail
print("\n=== last 12 messages ===")
for s in msgs[-12:]:
    print("  >>", repr(s[:90]))
# how many messages are non-trivial (len>2)
nt=sum(1 for s in msgs if len(s.strip())>2)
print("\nnon-trivial msgs:", nt, "/", len(msgs))
# STRT: total strings
print("STRT total bytes", len(STRT), " approx null-terminated utf16 strings:", STRT.count(b"\x00\x00"))
