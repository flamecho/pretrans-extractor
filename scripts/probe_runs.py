import os, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SPT_DIR = os.path.join(VNTRANS_HOME, "_work_koutari/iso/app/spt")

def decode(data):
    return bytes(b ^ 0xFF for b in data)

def enum_runs(path, minjp=1):
    raw = open(path, "rb").read()
    dec = decode(raw)
    # split on 0x00
    runs = dec.split(b"\x00")
    out = []
    for i, r in enumerate(runs):
        try:
            t = r.decode("cp932")
        except Exception:
            continue
        # count japanese-ish chars (hiragana/katakana/kanji)
        jp = sum(1 for c in t if 0x3040 <= ord(c) <= 0x30FF or 0x4E00 <= ord(c) <= 0x9FFF)
        if jp >= minjp:
            out.append(t)
    return out

# dump runs of opening.spt and kyoutuu.spt
for fn in ["opening.spt", "kyoutuu.spt"]:
    p = os.path.join(SPT_DIR, fn)
    runs = enum_runs(p)
    print(f"\n##### {fn}: {len(runs)} text runs (jp>=1) #####")
    for t in runs[:60]:
        # mark leading/trailing odd chars
        print(repr(t))
