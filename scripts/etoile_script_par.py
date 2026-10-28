# -*- coding: utf-8 -*-
"""DATA02 脚本解包（多进程版）"""
import multiprocessing as mp
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

G = {}


def init(root, outdir):
    from etoile_unpack import load_pair
    sizes, ents, data = load_pair(root + '/DATA02')
    G['ents'] = ents
    G['data'] = data
    G['names'] = [x for x in data[:sizes[0]].decode('cp932', 'replace').split('\r\n') if x]
    G['out'] = outdir
    os.makedirs(outdir, exist_ok=True)


def work(i):
    from etoile_script import unpack_entry
    o, s = G['ents'][i]
    try:
        key, outs = unpack_entry(G['data'][o:o + s])
    except Exception:
        return i, 0
    if not outs:
        return i, 0
    name = (G['names'][i] if i < len(G['names']) else 'x%d' % i).replace('/', '_')
    for k, b in enumerate(outs):
        open(os.path.join(G['out'], '%05d_%s_%d.scpt' % (i, name, k)), 'wb').write(b)
    return i, len(outs)


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(VNTRANS_HOME, '_src_etoile')
    outdir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(VNTRANS_HOME, '_work_etoile/scpt')
    jobs = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    from etoile_unpack import load_pair
    sizes, ents, _ = load_pair(root + '/DATA02')
    idx = list(range(1, len(ents)))
    ok = 0
    fails = []
    with mp.Pool(jobs, initializer=init, initargs=(root, outdir)) as pool:
        for n, (i, c) in enumerate(pool.imap_unordered(work, idx, chunksize=4), 1):
            if c:
                ok += 1
            else:
                fails.append(i)
            if n % 200 == 0:
                print('  %d/%d ok=%d' % (n, len(idx), ok), flush=True)
    print('ok=%d fail=%d' % (ok, len(fails)))
    print('fail idx:', fails[:40])


if __name__ == '__main__':
    main()
