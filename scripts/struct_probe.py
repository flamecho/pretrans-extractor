# -*- coding: utf-8 -*-
"""引号/括号结构探针：把「一行里塞了几个框」量化。

用户给的四个探针：
  `(?!^)「`  行中出现开引号        `(?<!^)(」)(?!$)`  `」` 两侧都有内容
  `(?!^)（`  行中出现开括号        `(?<!^)(）)(?!$)`  `）` 两侧都有内容
它们只能「提示有问题」，不能区分合法（内联引用/插入语）与缺陷（一行多框）。
本脚本按**配对结构**判定：

  A 引号不平衡  `「`数 ≠ `」`数        ⇒ 必有截断
  B 括号不平衡  `（`数 ≠ `）`数        ⇒ 必有截断
  C 引号多段    引号平衡但顶层「…」段 ≥2 ⇒ 一行塞了多个台词框
  D 括号多段    括号平衡但顶层（…）段 ≥2 ⇒ 一行塞了多个独白框

用法：
  python scripts/struct_probe.py 提取结果/*.txt
  python scripts/struct_probe.py <txt> -v --limit 20 --kind C
"""
import argparse
import glob
import io
import os
import sys

PAIRS = {'「': '」', '（': '）', '『': '』'}


def scan(s, op, cl):
    """返回 (配对列表[(i,j)], 未配对数, 顶层段数)"""
    stack, pairs, depth_top = [], [], 0
    for i, ch in enumerate(s):
        if ch == op:
            if not stack:
                depth_top += 1
            stack.append(i)
        elif ch == cl:
            if stack:
                pairs.append((stack.pop(), i))
    return pairs, len(stack), depth_top


def analyse(line):
    pq, uq, tq = scan(line, '「', '」')
    pp, up, tp = scan(line, '（', '）')
    kinds = []
    if uq or line.count('「') != line.count('」'):
        kinds.append('A')
    if up or line.count('（') != line.count('）'):
        kinds.append('B')
    if tq >= 2:
        kinds.append('C')
    if tp >= 2:
        kinds.append('D')
    return kinds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('paths', nargs='+')
    ap.add_argument('-v', '--verbose', action='store_true')
    ap.add_argument('--limit', type=int, default=8)
    ap.add_argument('--kind', default='')
    a = ap.parse_args()

    paths = []
    for p in a.paths:
        if os.path.exists(p):
            paths.append(p)
        else:
            paths.extend(sorted(glob.glob(p)))

    tot = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
    print('%-40s %5s %5s %5s %5s' % ('作品', 'A失衡「', 'B失衡（', 'C多段「', 'D多段（'))
    for p in paths:
        if not p.endswith('.txt'):
            continue
        L = [x for x in io.open(p, encoding='utf-8-sig').read().split('\n') if x.strip()]
        cnt = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
        samples = []
        for i, x in enumerate(L, 1):
            ks = analyse(x)
            for k in ks:
                cnt[k] += 1
            if ks and a.kind and a.kind in ks:
                samples.append((i, ks, x))
        for k in cnt:
            tot[k] += cnt[k]
        if any(cnt.values()):
            print('%-40s %5d %5d %5d %5d' % (os.path.basename(p)[:-4][:40], cnt['A'], cnt['B'], cnt['C'], cnt['D']))
        if a.verbose and samples:
            print('  --- 样例（kind=%s）' % a.kind)
            for i, ks, x in samples[:a.limit]:
                print('   L%-6d %s %s' % (i, ''.join(ks), x[:100]))
    print('%-40s %5d %5d %5d %5d' % ('合计', tot['A'], tot['B'], tot['C'], tot['D']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
