import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
SPT=os.path.join(VNTRANS_HOME, "_work_koutari/iso/app/spt")
def dec(d): return bytes(b^0xFF for b in d)
fn="Akaru_route1.spt"
raw=open(os.path.join(SPT,fn),"rb").read()
data=dec(raw)
needles=["っラン","て走る","泊魔","髄魔","走る準備","ランニングウェアに着替え"]
for nd in needles:
    bn=nd.encode("cp932")
    idx=data.find(bn)
    if idx<0:
        print(f"[ {nd!r} ] NOT FOUND"); continue
    # show 24 bytes before (raw and decoded), the needle, and 24 after
    s=max(0,idx-24); e=min(len(data),idx+len(bn)+24)
    seg_raw=raw[s:e]; seg_dec=data[s:e]
    print(f"\n[ {nd!r} ] @dec-offset {idx}")
    print("  raw:", " ".join(f"{b:02X}" for b in seg_raw))
    print("  dec:", seg_dec.decode("cp932","replace"))
    # also show the run boundaries: find the null before and after
    pre=data.rfind(b"\x00",0,idx); nxt=data.find(b"\x00",idx)
    print(f"  run start offset (after prev null): {pre+1}  run end (next null): {nxt}")
    run=data[pre+1:nxt]
    print("  FULL RUN:", run.decode("cp932","replace"))
