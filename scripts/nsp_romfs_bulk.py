#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NSP 内 romfs 批量就地提取（按正则/大小筛选），一次开 NCA 多次落盘。

用法:
  python scripts/nsp_romfs_bulk.py <nsp> --out <dir> [--include REGEX] [--exclude REGEX] [--maxsize N] [--list-only]
"""
import sys, os, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nsp_plainromfs as W4


def main():
    path = sys.argv[1]
    args = sys.argv[2:]
    opt = lambda k, d=None: args[args.index(k) + 1] if k in args else d
    out = opt('--out')
    inc = re.compile(opt('--include', '.'))
    exc = re.compile(opt('--exclude', r'^$'))
    mx = int(opt('--maxsize', '0') or 0)
    n, v, comp = W4.open_nsp(path)
    if comp[0] or comp[1]:
        raise SystemExit('压缩段，不适用')
    files, fd = W4.parse_romfs(v)
    sel = [f for f in files if inc.search(f[0]) and not exc.search(f[0]) and (mx == 0 or f[2] <= mx)]
    print('[i] 选中 %d / %d' % (len(sel), len(files)))
    for nm, o, s in sel:
        if '--list-only' in args:
            print('%12d  %s' % (s, nm))
            continue
        p = os.path.join(out, nm.replace('/', os.sep))
        os.makedirs(os.path.dirname(p) or '.', exist_ok=True)
        with open(p, 'wb') as w:
            for k in range(0, s, 1 << 23):
                w.write(v.read(o + k, min(1 << 23, s - k)))
        print('   -> %s (%d)' % (nm, s))


if __name__ == '__main__':
    main()
