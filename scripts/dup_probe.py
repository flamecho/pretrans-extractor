# -*- coding: utf-8 -*-
"""双版拼接探针：找「同一行内同一句出现两次」的行。

缺陷：源数据同一句存两份（字面名版 / 宏回填名版，或点名版 / 泛称版），
提取时两版被拼进同一行 ⇒ 引号可能平衡（`「A「B」」`、`（A）（B）`、无引号的地の文），
所以「引号不平衡」只能抓到一半。本探针用**行内重复子串**抓全量。

判据：
1. 行内所有「已知名字」（--alias，逗号分隔）统一替换成占位符 `@`；
2. 去掉空白与全角空格后，滑动窗口找长度 ≥ --min 的重复子串；
3. 命中 ⇒ 疑似双版，输出：行号 / 重复片段 / 原文。

用法：
  python scripts/dup_probe.py 提取结果/*.txt --alias 義経,遮那 --min 10
  python scripts/dup_probe.py <txt> --alias a,b -v --limit 20
"""
import argparse
import glob
import io
import os
import re
import sys


def norm(s, lits):
    for lit in sorted(lits, key=len, reverse=True):
        s = s.replace(lit, '@')
    return re.sub(r'[\s\u3000]', '', s)


def first_dup(t, n):
    seen = set()
    for i in range(len(t) - n + 1):
        g = t[i:i + n]
        if g in seen:
            return g
        seen.add(g)
    return None


def probe(path, lits, n, verbose=False, limit=0):
    lines = [x for x in io.open(path, encoding='utf-8-sig').read().split('\n') if x.strip()]
    hits = []
    for i, x in enumerate(lines, 1):
        if len(x) < n * 2:
            continue
        d = first_dup(norm(x, lits), n)
        if d:
            hits.append((i, d, x))
    print('=== %s  行数 %d  疑似双版 %d' % (os.path.basename(path)[:-4][:44], len(lines), len(hits)))
    if verbose:
        for i, d, x in hits[:limit or len(hits)]:
            print('  L%-6d 重复[%s]\n        %s' % (i, d, x[:110]))
    return len(lines), hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('paths', nargs='+')
    ap.add_argument('--alias', default='', help='已知名字，逗号分隔（替换成占位符后再比）')
    ap.add_argument('--min', type=int, default=10, help='重复片段最小长度')
    ap.add_argument('-v', '--verbose', action='store_true')
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()

    lits = [x for x in a.alias.split(',') if x]
    paths = []
    for p in a.paths:
        if os.path.exists(p):
            paths.append(p)
        else:
            paths.extend(sorted(glob.glob(p)))

    total = 0
    for p in paths:
        if not p.endswith('.txt'):
            continue
        _, hits = probe(p, lits, a.min, a.verbose, a.limit)
        total += len(hits)
    print('\n合计疑似双版行 %d（%d 部）' % (total, len(paths)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
