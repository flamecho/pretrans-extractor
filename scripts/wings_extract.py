import sys, struct, os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
import advhd
from am2_extract import load_arc, _cstr, G as G0, S as S0, D

ARC = os.path.join(VNTRANS_HOME, '_work_wings/iso/RIO.ARC')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[JP]Wings Innocent.txt')
G = dict(G0); G.update({0x4D: 5, 0x66: 32})
S = dict(S0); S.update({0x25: 3})

def parse(b):
    i, n = 0, len(b); out = []; closed = False
    while i < n:
        op = b[i]; i += 1
        if op == 0xFF:
            if i == n:
                closed = True; break
            if b[i] == 0xFF:
                i += 5; _, i = _cstr(b, i); continue
            i += 8; continue
        if op == 0x02:
            nch = struct.unpack_from('<H', b, i)[0]; i += 2
            for _ in range(nch):
                i += 2; s, i = _cstr(b, i); o2 = b[i]; i += 1
                if o2 in D: i += D[o2]; _, i = _cstr(b, i); _, i = _cstr(b, i)
                elif o2 in S: i += S[o2]; _, i = _cstr(b, i)
                elif o2 in G: i += G[o2]
                else: raise ValueError('choice target %02X' % o2)
                out.append(('opt', s))
            continue
        if op in D:
            i += D[op]; _, i = _cstr(b, i); line, i = _cstr(b, i)
            out.append(('dlg', line))
        elif op in S:
            i += S[op]; s, i = _cstr(b, i)
            if op in (0x41, 0xB6): out.append(('nar', s))
        elif op in G:
            i += G[op]
        else:
            raise ValueError('unknown %02X @0x%X' % (op, i))
        if i > n: raise ValueError('overrun')
    return out, closed

def to_text(raw):
    return raw.decode('cp932', 'replace').replace('\\n', '').strip()

entries = load_arc(ARC)
lines = []; stats = {}; bad = []; skipped = []
for nm, ln, b in entries:
    if not nm.startswith('WI_'):
        skipped.append(nm); continue
    try:
        seq, ok = parse(b)
    except ValueError as e:
        bad.append((nm, str(e))); continue
    if not ok: bad.append((nm, '未走到末字节'))
    for kind, s in seq:
        t = to_text(s)
        if t:
            lines.append(t); stats[kind] = stats.get(kind, 0) + 1

print('scripts', len(entries), 'included', len(entries) - len(skipped), 'skipped', len(skipped), 'bad', len(bad))
print('lines', len(lines), 'stats', stats)
for x in bad[:10]: print('BAD', x)
data = ('\n'.join(lines) + '\n').encode('utf-8')
open(OUT, 'wb').write(b'\xef\xbb\xbf' + data)
print('wrote', OUT, len(lines), len(data))
print('quotes', sum(x.count('「') for x in lines), sum(x.count('」') for x in lines))
print('parens', sum(x.count('（') for x in lines), sum(x.count('）') for x in lines))
print('openq', sum(1 for x in lines if x.count('「') > x.count('」')), 'closeq', sum(1 for x in lines if x.count('」') > x.count('「')))
print('openp', sum(1 for x in lines if x.count('（') > x.count('）')), 'closep', sum(1 for x in lines if x.count('）') > x.count('（')))
