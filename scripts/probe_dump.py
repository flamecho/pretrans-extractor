import sys, os, re
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SPT_DIR = os.path.join(VNTRANS_HOME, "_work_koutari/iso/app/spt")

def decode(data):
    return bytes(b ^ 0xFF for b in data)

def find_and_dump(path, needles, ctx=40):
    raw = open(path, "rb").read()
    dec = decode(raw)
    print(f"=== {os.path.basename(path)} size={len(raw)} ===")
    for nd in needles:
        bn = nd.encode("cp932")
        idx = dec.find(bn)
        if idx < 0:
            print(f"  [needle {nd!r}] NOT FOUND")
            continue
        start = max(0, idx - ctx)
        end = min(len(dec), idx + len(bn) + ctx)
        seg = dec[start:end]
        print(f"  [needle {nd!r}] @offset {idx} (decoded); raw bytes:")
        # show hex of raw segment
        raw_seg = raw[start:end]
        hexs = " ".join(f"{b:02X}" for b in raw_seg)
        print("   raw:", hexs)
        # cp932 decode best-effort
        try:
            txt = seg.decode("cp932", errors="replace")
        except Exception as e:
            txt = repr(seg)
        print("   dec:", txt)

# prologue file
files = ["opening.spt", "opening2.spt", "kyoutuu.spt"]
needles = ["獅ばらく", "走る", "ランニングウェア", "泊魔", "髄魔", "着替え"]
for f in files:
    p = os.path.join(SPT_DIR, f)
    if os.path.exists(p):
        find_and_dump(p, needles)
