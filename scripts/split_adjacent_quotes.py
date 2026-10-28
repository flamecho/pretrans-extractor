#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""句中 `」「` 相邻的筛查／拆分工具（skill `references/S6-lines.md` §「句中引号只作探针」的落地）。

判据思路（必须先看数据再动手，禁止盲拆）：
  - 一行里出现 `」「` ⇒ 至少两个文本框被并进一行（**一次点击＝一行**被破坏）
  - 若两段**高度相似**（difflib ratio ≥ --ratio，默认 0.82）⇒ 判为「同一句的两个变体」
    （典型：`「義経様…」「遮那王様…」` = 名字宏版与字面版并存）⇒ **去重留一个**
  - 否则判为「两个不同的人／两句不同的话被并」⇒ **拆成两行**

用法：
  python scripts/split_adjacent_quotes.py <成品.txt> --dry          # 只统计与样例
  python scripts/split_adjacent_quotes.py <成品.txt> --apply        # 写回（自动备份）
  python scripts/split_adjacent_quotes.py --all --dry               # 全部 27 部
选项：
  --ratio 0.82     相似度阈值（越高越保守，越容易判成「拆分」）
  --keep first|last|name   变体去重时保留哪一段（默认 name：含 --name 指定词的优先）
  --name 遮那王     判变体保留时优先匹配的名字
"""
import argparse
import difflib
import io
import os
import re
import shutil
import sys

T = '提取结果'
SEG = re.compile(r'「[^「」]*」')


def analyse(line, ratio, keep, name):
    """返回 (action, segments)：action ∈ {'none','split','dedupe'}"""
    if '」「' not in line:
        return 'none', []
    if not (line.startswith('「') and line.endswith('」')):
        return 'none', []          # 前后还有地の文 ⇒ 交给人工
    segs = SEG.findall(line)
    if len(segs) < 2 or ''.join(segs) != line:
        return 'none', []
    # 变体判定：所有相邻对相似度都高
    ratios = [difflib.SequenceMatcher(None, segs[i], segs[i + 1]).ratio() for i in range(len(segs) - 1)]
    if ratios and min(ratios) >= ratio:
        if keep == 'name' and name:
            keepidx = next((i for i, s in enumerate(segs) if name in s), len(segs) - 1)
        elif keep == 'last':
            keepidx = len(segs) - 1
        else:
            keepidx = 0
        return 'dedupe', [segs[keepidx]]
    return 'split', segs


def process(path, dry, ratio, keep, name, verbose):
    L = [x for x in io.open(path, encoding='utf-8-sig').read().split('\n') if x.strip()]
    out = []
    nspl = nded = 0
    samples = []
    for x in L:
        act, segs = analyse(x, ratio, keep, name)
        if act == 'split':
            out.extend(segs)
            nspl += 1
            if len(samples) < 6:
                samples.append(('split', x, segs))
        elif act == 'dedupe':
            out.extend(segs)
            nded += 1
            if len(samples) < 6:
                samples.append(('dedupe', x, segs))
        else:
            out.append(x)
    print('=== %s' % os.path.basename(path)[:-4])
    print('   行 %d → %d ｜拆分 %d 行（+%d）｜变体去重 %d 行（-%d）｜原样 %d'
          % (len(L), len(out), nspl, nspl, nded, nded, len(L) - nspl - nded))
    if verbose:
        for act, x, segs in samples:
            print('   [%s] %s' % (act, x[:80]))
            print('        → %s' % ' ／ '.join(s[:40] for s in segs))
    if not dry:
        shutil.copy(path, '_bak_patch/%s.txt.preSplit' % os.path.basename(path)[:-4])
        io.open(path, 'w', encoding='utf-8-sig', newline='\n').write('\n'.join(out) + '\n')
        print('   已写回（备份 .preSplit）')
    return nspl, nded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='*')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--ratio', type=float, default=0.82)
    ap.add_argument('--keep', default='name', choices=['first', 'last', 'name'])
    ap.add_argument('--name', default='')
    ap.add_argument('-v', action='store_true')
    a = ap.parse_args()
    targets = a.files or ([os.path.join(T, f) for f in sorted(os.listdir(T)) if f.endswith('.txt')] if a.all else [])
    tp = td = 0
    for p in targets:
        s, d = process(p, a.dry or not a.apply, a.ratio, a.keep, a.name, a.v)
        tp += s
        td += d
    print('\n合计：拆分 %d 行 ｜ 变体去重 %d 行' % (tp, td))


if __name__ == '__main__':
    main()
