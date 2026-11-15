import sys, struct, os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
from am2_extract import load_arc, _cstr, G as G0, S as S0, D
G = dict(G0); G.update({0x4D: 5, 0x66: 32})
S = dict(S0); S.update({0x25: 3})
ARC = os.path.join(VNTRANS_HOME, '_work_wings/iso/RIO.ARC')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[JP]Wings Innocent.txt')

def parse(b):
    i, n = 0, len(b); out = []
    while i < n:
        op = b[i]; i += 1
        if op == 0xFF:
            if i == n: break
            if b[i] == 0xFF: i += 5; _, i = _cstr(b, i); continue
            i += 8; continue
        if op == 0x02:
            nch = struct.unpack_from('<H', b, i)[0]; i += 2
            for _ in range(nch):
                i += 2; s, i = _cstr(b, i); o2 = b[i]; i += 1
                if o2 in D: i += D[o2]; _, i = _cstr(b, i); _, i = _cstr(b, i)
                elif o2 in S: i += S[o2]; _, i = _cstr(b, i)
                elif o2 in G: i += G[o2]
                else: raise ValueError('choice')
                out.append(('opt', None, s))
            continue
        if op in D:
            pr = b[i:i+D[op]]; i += D[op]; _, i = _cstr(b, i); ln, i = _cstr(b, i)
            out.append(('text', pr[0], ln))
        elif op in S:
            pr = b[i:i+S[op]]; i += S[op]; s, i = _cstr(b, i)
            if op in (0x41, 0xB6): out.append(('text', pr[0], s))
        elif op in G: i += G[op]
        else: raise ValueError
    return out

def clean(raw):
    return raw.decode('cp932', 'replace').replace('\\n', '').strip()

pages = []; opts = []; ids = []
for nm, ln, b in load_arc(ARC):
    if not nm.startswith('WI_'): continue
    for kind, mid, raw in parse(b):
        if kind == 'text':
            t = clean(raw)
            if t:
                pages.append(t); ids.append(mid)
        else:
            t = clean(raw)
            if t: opts.append(t)
same = sum(1 for i in range(len(ids)-1) if ids[i] == ids[i+1])
print('S1 text records/clicks =', len(pages))
print('S2 pages (message-id boundary) =', len(pages), '| same-id adjacent pairs =', same)
print('S3 distribution: 1 click/page =', len(pages) - same, '| >=2 clicks/page =', same)
print('options =', len(opts))
expected = '\n'.join(pages + [])  # options are interleaved in real order; rebuild below
# rebuild in actual order
lines = []
for nm, ln, b in load_arc(ARC):
    if not nm.startswith('WI_'): continue
    for kind, mid, raw in parse(b):
        t = clean(raw)
        if t: lines.append(t)
actual = open(OUT, encoding='utf-8-sig').read().splitlines()
print('rebuilt lines =', len(lines), '| output lines =', len(actual), '| exact match =', lines == actual)
print('multi-click pages = 0 -> single version; 整页行 should be 0')
