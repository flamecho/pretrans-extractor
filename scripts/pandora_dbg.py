# -*- coding: utf-8 -*-
import struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pandora_extract import load, code_range, scan_strings, BREAK_CMDS, A4

d, ents = load()

def find_file(addr):
    for e in ents:
        a = e[1] * 0x800
        if a <= addr < a + e[3]:
            return e
    return None

target = int(sys.argv[1], 16)
lo = target - int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x1200
hi = target + int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x1200
e = find_file(target)
print("file", e)
cs, ce = code_range(d, e[1] * 0x800)
i = cs
while i < ce:
    bs = struct.unpack_from('<I', d, i)[0]
    if bs == 0 or bs % 4 or i + bs > len(d):
        print("BAD", hex(i), hex(bs)); break
    pay = d[i + 4:i + bs]
    if i + bs < target - lo:
        i += bs; continue
    if i > target + hi:
        break
    info = []
    if len(pay) == 12:
        a0, cmd, fl = struct.unpack_from('<3I', pay, 0)
        info.append(f"12B a={a0:x} cmd={cmd:x} fl={fl}")
        if a0 == 0 and cmd in BREAK_CMDS:
            info.append("### BREAK")
    ss = scan_strings(pay)
    for k, s in ss:
        info.append(f"@+{k} {s!r}")
    print(hex(i), "sz", hex(bs), "|", " ; ".join(info))
    i += bs
