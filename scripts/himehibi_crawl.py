#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import himehibi_disasm as H

ents, SCRIPTS = H.load()
# case-insensitive name map
def norm(n):
    n = n.strip().lower()
    if n.endswith(".scr"):
        n = n[:-4]
    return n

NAME2 = {norm(n): n for n in SCRIPTS}

def calls_of(name):
    """ordered list of callee script names (0x1e / 0x1d)."""
    b = SCRIPTS[name]
    res, err = H.disasm(b)
    out = []
    for off, op, size, ident, ops in res:
        if op in (0x1d, 0x1e):
            ss = [v for t, v in ops if isinstance(v, str)]
            if len(ss) >= 2:
                out.append(ss[0])
        elif op == 0x0102:  # register-like (INIT SELECT2)
            pass
    return out

def crawl(root):
    order = []
    seen = set()
    def rec(name):
        key = norm(name)
        if key in seen:
            return
        if key not in NAME2:
            return
        seen.add(key)
        order.append(NAME2[key])
        for callee in calls_of(NAME2[key]):
            rec(callee)
    rec(root)
    return order

if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "PRG_MAIN_0630"
    order = crawl(root)
    print(f"reachable from {root}: {len(order)} scripts")
    for i, n in enumerate(order):
        print(f"  {i:3d} {n}")
