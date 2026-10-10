#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""蝶の毒 華の鎖 ～幻想夜話～  残存化けの統計的検出

「バイグラム言語モデルで見て不自然な文字」を検出する（全探索・総当りはしない）。
検出した位置は scripts/gensou_decode.FIXES の確定復元表で修正する。
"""
import sys, os, pickle
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xp3 import XP3
import gensou_decode as GD


def main():
    arc = os.path.join(VNTRANS_HOME, '_work_gensou/_iso/poisonchain_fd/data.xp3')
    x = XP3(arc)
    cm, bg = GD.build_models(x)
    names = sorted(n for n in x.files
                   if n.startswith('scenario/') and n.endswith('.txt'))
    rows = []
    for n in names:
        dec, _ = GD.decode(x.read(n), cm, bg, n)
        t = dec.decode('cp932', 'replace')
        lows = []
        for k in range(2, len(t) - 1):
            if t[k] in '\r\n':
                continue
            lp = bg.pair_lp(t[k - 1], t[k]) + bg.pair_lp(t[k], t[k + 1])
            lows.append((lp, k))
        lows.sort()
        for lp, k in lows[:6]:
            if lp > -15:
                break
            off = len(t[:k].encode('cp932', 'replace'))
            ctx = ''.join(c for c in t[max(0, k - 14):k + 14] if c not in '\r\n')
            rows.append((lp, n, off, t[k], ctx))
    rows.sort()
    for lp, n, off, ch, ctx in rows:
        print('%-22s @byte%-7d ch=%r lp=%6.1f  %s' % (n.split('/')[-1], off, ch, lp, ctx))
    print('total flagged', len(rows))


if __name__ == '__main__':
    main()
