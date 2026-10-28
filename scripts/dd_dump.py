# -*- coding: utf-8 -*-
"""把 7drops.scenarios.asset 里所有 .book 摊平成 TSV 供人工判读语义。"""
import sys, struct, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import UnityPy
from dd_utage import parse_book

BUNDLE = sys.argv[1]
OUT = sys.argv[2]
env = UnityPy.load(BUNDLE)
rows_out = []
for o in env.objects:
    if o.type.name != 'MonoBehaviour':
        continue
    raw = o.get_raw_data()
    n = struct.unpack_from('<I', raw, 0x1c)[0]
    nm = raw[0x20:0x20 + n].decode('utf-8', 'replace')
    if not nm.endswith('.book'):
        continue
    try:
        b = parse_book(raw)
    except Exception:
        continue
    for si, s in enumerate(b['sheets']):
        hdr = None
        for r in s['rows']:
            if r['index'] == s['header_row']:
                hdr = r['cells']
                break
        for r in s['rows']:
            c = r['cells']
            rec = dict(zip(hdr, c)) if hdr else {}
            rows_out.append((nm, si, s['name'], r['index'], rec, c))
with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
    for nm, si, sn, idx, rec, c in rows_out:
        cols = ' | '.join('%s=%s' % (k, v) for k, v in rec.items() if v.strip())
        f.write('%s\t%d\t%s\t%d\t%s\n' % (nm, si, sn.split(':')[-1], idx, cols))
print('rows', len(rows_out))
