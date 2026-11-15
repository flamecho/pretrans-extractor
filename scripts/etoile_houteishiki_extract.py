# -*- coding: utf-8 -*-
"""[JP]エトワールの方程式 extractor. L0: RE_NOTES.md (Etoile.exe 0x415E60/0x404770/0x419C30/0x419CD0/0x41A1A8/0x41A370)."""
import struct, os, io, sys, glob
from collections import Counter, OrderedDict

SZ = {0:264,1:4,2:68,3:68,4:8,5:4,6:80,7:16,8:272,9:16,12:8,13:276,14:272,
      15:12,16:12705,17:4,18:208,19:1548,20:272,21:12,22:276,23:12}
DEC = 'scr_dec'

def walk(d):
    assert d[:4] == b'SCRT'
    n = struct.unpack_from('<I', d, 4)[0]
    o = 8
    for _ in range(n):
        t = struct.unpack_from('<I', d, o)[0]
        yield t, o
        o += SZ[t]
    assert o == len(d), (o, len(d))

def cp(b):
    return b.split(b'\x00')[0].decode('cp932')

def merge(b):
    return cp(b).replace('\x0a', '')

members = OrderedDict()
for p in sorted(glob.glob(os.path.join(DEC, '*.bin'))):
    members[os.path.basename(p)[:-4]] = open(p, 'rb').read()

calls = {}
for name, d in members.items():
    calls[name] = [cp(d[o+4:o+4+64])[:-4] for t, o in walk(d) if t == 0]
called = set(c for cs in calls.values() for c in cs)
roots = [n for n in members if n not in called]
order = []
seen = set()
def dfs(n):
    if n in seen or n not in members:
        return
    seen.add(n)
    order.append(n)
    for c in calls[n]:
        dfs(c)
for r in roots:
    dfs(r)
for n in members:
    dfs(n)

lines = []
stats = Counter()
names = Counter()
charcount_mismatch = []
for name in order:
    d = members[name]
    for t, o in walk(d):
        if t == 16:
            stats['messages'] += 1
            nm = cp(d[o+4:o+29])
            pc = struct.unpack_from('<I', d, o+12445)[0]
            for pg in range(pc):
                raw = d[o+8349+pg*128:o+8349+pg*128+128]
                txt = merge(raw)
                cc = struct.unpack_from('<I', d, o+12449+pg*4)[0]
                if cc != len(cp(raw)):
                    charcount_mismatch.append((name, o, pg, cc, len(cp(raw))))
                stats['pages'] += 1
                if nm:
                    names[nm] += 1
                    if txt[:1] in ('（', '('):
                        lines.append(nm + txt)          # 心声/独白：原文括号，不加「」
                    else:
                        lines.append(nm + '「' + txt + '」')  # 台词：统一加「」
                else:
                    lines.append(txt)
        elif t == 18:
            stats['selects'] += 1
            items = cp(d[o+4:o+132]).split('\x0a')
            for it in items:
                it = it.lstrip('\u3000')
                if it:
                    stats['choice_items'] += 1
                    lines.append(it)
with open(sys.argv[1] if len(sys.argv) > 1 else 'draft1.txt', 'w', encoding='utf-8-sig', newline='\n') as f:
    for l in lines:
        f.write(l + '\n')
print('members', len(members), 'roots', roots)
print('order reach', len(order), 'of', len(members))
print('stats', dict(stats))
print('lines', len(lines))
print('names', names.most_common())
print('charcount mismatches', len(charcount_mismatch), charcount_mismatch[:5])
