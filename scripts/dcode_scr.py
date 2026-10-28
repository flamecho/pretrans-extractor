"""GSS / SCR3 脚本批量解码入口（复用 `himehibi_lsdarc` 与 `gss_scr3` 两个库）。"""
import os, sys, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import himehibi_lsdarc as L
import gss_scr3 as D

ROM = '_work_dcode/romfs'
OUT = '_work_dcode/scr'


def main():
    ents, end = L.read_index(os.path.join(ROM, 'SCRDATA.BIN'))
    arc = open(os.path.join(ROM, 'SCRDATA.ARC'), 'rb').read()
    print('count', len(ents), 'indexEnd', hex(end), 'arc', len(arc))
    os.makedirs(OUT, exist_ok=True)
    ok = bad = 0
    errs = collections.Counter()
    ops = collections.Counter()
    opstr = collections.defaultdict(collections.Counter)
    for e in ents:
        b = arc[e['off']:e['off'] + e['usz']]
        open(os.path.join(OUT, e['name'] + '.BIN'), 'wb').write(b)
        if b[:8] != b'SCR 3.00':
            print('MAGIC?', e['name'], b[:8])
            continue
        res, err = D.disasm(b)
        if err:
            bad += 1
            errs[(e['name'],) + err[1:]] += 1
        else:
            ok += 1
        for off, op, size, ident, o in res:
            ops[op] += 1
            ns = sum(1 for t, v in o if t == 3)
            if ns:
                opstr[op][ns] += 1
    print('disasm ok', ok, 'bad', bad)
    print('errors', errs.most_common(5))
    print('ops with strings:')
    for op, c in sorted(opstr.items()):
        print('  op=%#06x count=%d pat=%s' % (op, ops[op], dict(opstr[op])))
    print('names:')
    print(' '.join(e['name'] for e in ents))


main()
