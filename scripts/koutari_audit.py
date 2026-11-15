# -*- coding: utf-8 -*-
"""audit all 16 .spt: dump first samples + counts to decide include/exclude."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import koutari_extract2 as K

SPT = K.SRC
order = [l.strip() for l in open(K.ORDER_FILE, 'rb').read().decode('cp932', 'ignore').splitlines() if l.strip()]

PLATES = set(K.MARKERS) | K.mine_plates(
    {n: K.decrypt(os.path.join(SPT, n + '.spt')) for n in order if os.path.exists(os.path.join(SPT, n + '.spt'))})

for name in order:
    p = os.path.join(SPT, name + '.spt')
    if not os.path.exists(p):
        print(f"\n### {name}: MISSING"); continue
    n = K.decrypt(p)
    r = K.find_pools(n)
    if not r:
        print(f"\n### {name}: NOPOOL"); continue
    w1, ph1 = K.read_pool(n, r[0])
    body = K.extract_pool1(n, w1)
    w2, ph2 = K.read_pool(n, r[1]) if r[1] else ([], 0)
    extra = K.extras_in_order(n, w2) if w2 else []
    excl = name in K.EXCLUDE
    tag = 'EXCLUDE' if excl else 'INCLUDE'
    print(f"\n### {name} [{tag}] ph1={ph1} ph2={ph2} body={len(body)} extra={len(extra)}")
    for s in body[:6]:
        print('   B|', s[:70])
    for s in extra[:6]:
        print('   X|', s[:70])
