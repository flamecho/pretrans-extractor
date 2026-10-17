#!/usr/bin/env python3
"""pending.py —— **未落位检测**：哪些作品提完了却还没进索引。

问题：收尾靠脑子记。做完了、忘了落 `WORKS` 的作品，下次查「做过没」就查不到，
于是重做一遍。本工具把这件事变成一次扫描。

检查三种状态:
  ① 有成品 txt，但没有解析报告        → 报告没写
  ② 有报告，但作品名不在任何 `WORKS-*.md` → 没落位（跑 `archive_work.py --apply`）
  ③ 有报告且已落位，但报告头没有 front-matter → 下次索引字段只能猜（提示补头）

用法:
  python scripts/pending.py                       # 扫当前目录的 提取结果/ 与 `references/`
  python scripts/pending.py --out <提取结果目录> --mem <memory 目录> --since 2026-10-01
退出码: 0 = 无待办; 1 = 有待办
"""
import argparse
import glob
import io
import os
import re
import sys

PREFIX = re.compile(r'^\[[^\]]*\]\s*')


def read(p):
    with io.open(p, encoding='utf-8', errors='replace', newline='') as f:
        return f.read()


def norm(s):
    s = PREFIX.sub('', s)
    s = re.sub(r'_全文本\.txt$|_解析报告\.md$|_分析报告\.md$', '', s)
    s = re.sub(r'\s*[—\-–·]\s*全文本提取\s*$', '', s)
    return s.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(os.getcwd(), '提取结果'))
    ap.add_argument('--mem', default=os.path.join(os.getcwd(), '.workbuddy', 'memory'))
    ap.add_argument('--since', help='只看该日期之后修改的文件（YYYY-MM-DD）')
    ap.add_argument('--skip', default=r'_変体分岐メモ|_メモ$',
                    help='文件名匹配则跳过（备忘录/非作品）')
    a = ap.parse_args()

    if not os.path.isdir(a.out):
        print('[!!] 找不到成品目录：%s' % a.out)
        return 2

    since = None
    if a.since:
        import datetime
        since = datetime.datetime.strptime(a.since, '%Y-%m-%d').timestamp()

    def fresh(p):
        return since is None or os.path.getmtime(p) >= since

    txts = {}
    for p in glob.glob(os.path.join(a.out, '*.txt')):
        if fresh(p):
            txts[norm(os.path.basename(p))] = p
    reps = {}
    for p in glob.glob(os.path.join(a.out, '解析报告', '*.md')):
        if re.search(a.skip, os.path.basename(p)):
            continue
        if fresh(p):
            reps[norm(os.path.basename(p))] = p

    works = ''
    for p in glob.glob(os.path.join(a.mem, 'WORKS*.md')):
        works += read(p)

    no_report, no_index, no_head, ok = [], [], [], 0
    for name, rp in reps.items():
        if name not in works:
            no_index.append((name, rp))
        else:
            ok += 1
        # ③ 只对**尚未落位**的新作提示（老报告早就进了索引，补头没有收益）
        if name not in works and not re.match(r'^\ufeff?---\s*\n', read(rp)):
            no_head.append((name, rp))
    for name, tp in txts.items():
        if name not in reps:
            no_report.append((name, tp))

    def show(title, rows, hint):
        if not rows:
            return
        print('\n== %s（%d）==' % (title, len(rows)))
        for n, p in rows[:15]:
            print('  %-46s %s' % (n[:46], os.path.basename(p)[:40]))
        if len(rows) > 15:
            print('  … 另有 %d' % (len(rows) - 15))
        print('  → ' + hint)

    show('① 有成品、无报告', no_report, '补 `scripts/archive_work.py --template --out ...`')
    show('② 有报告、未进索引', no_index, '跑 `archive_work.py --report <报告> --apply`')
    show('③ 已落位但报告没 front-matter', no_head, '补 6 行头（见 05-external-report §4.1）')

    print('\n--- 成品 %d ｜ 报告 %d ｜ 已落位 %d ｜ 待办 %d ---'
          % (len(txts), len(reps), ok, len(no_report) + len(no_index) + len(no_head)))
    return 1 if (no_report or no_index or no_head) else 0


if __name__ == '__main__':
    sys.exit(main())
