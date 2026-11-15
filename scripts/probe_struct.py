import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
SPT=os.path.join(VNTRANS_HOME, "_work_koutari/iso/app/spt")
def dec(d): return bytes(b^0xFF for b in d)
fn="Akaru_route1.spt"
raw=open(os.path.join(SPT,fn),"rb").read()
data=dec(raw)
# all null positions
nulls=[i for i,b in enumerate(data) if b==0]
print(f"file {fn} size={len(data)} nulls={len(nulls)}")
# runs in region
lo,hi=677700,678100
# build runs globally then filter
runs=[]
for k in range(len(nulls)-1):
    a=nulls[k]+1; b=nulls[k+1]
    if b<=a: continue
    seg=data[a:b]
    runs.append((a,b,seg))
print(f"total runs={len(runs)}")
# print runs that overlap region
for a,b,seg in runs:
    if a>hi or b<lo: continue
    try: t=seg.decode("cp932")
    except Exception as e: t="<DECERR>"
    # escape control chars
    esc=t.replace("\r","\\r").replace("\n","\\n").replace("\t","\\t")
    print(f"  off={a} len={b-a} hex={seg.hex()} dec={esc!r}")
