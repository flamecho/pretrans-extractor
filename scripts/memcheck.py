#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查记忆入口大小，并列出技能文档体积。

文档按主题组织，不按字节阈值拆分。MEMORY.md 超过 8 KB 返回错误；
历史日志超过 30 KB 仅提示按章节查询。

python scripts/memcheck.py --mem DIR --skill DIR --top 40
退出码：0 无入口大小错误；1 MEMORY.md 超限。"""
import argparse
import glob
import os
import sys

DEFAULT_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not os.path.isfile(os.path.join(DEFAULT_SKILL, 'SKILL.md')):
    DEFAULT_SKILL = os.path.expanduser('~/.workbuddy/skills/vn-custom-bytecode-text')


def kb(n):
    return n / 1024.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mem', default=os.path.join(os.getcwd(), '.workbuddy', 'memory'))
    ap.add_argument('--skill', default=DEFAULT_SKILL)
    ap.add_argument('--top', type=int, default=40)
    a = ap.parse_args()

    err = 0
    out = []
    for root, label, pats in (
            (a.mem, '工作区记忆', ['*.md']),
            (a.skill, 'skill', ['SKILL.md', 'references/**/*.md'])):
        files = []
        for pat in pats:
            files += glob.glob(os.path.join(root, pat), recursive=True)
        files = [f for f in files if os.path.isfile(f)]
        if not files:
            continue
        out.append('\n== %s  (%s) ==' % (label, root))
        rows = []
        for f in files:
            s = os.path.getsize(f)
            name = os.path.relpath(f, root)
            is_log = name[:4].isdigit() and name.endswith('.md')
            flag = ''
            if os.path.basename(f) == 'MEMORY.md' and s > 8 * 1024:
                flag = '  [E] 自动注入文件超 8 KB ⇒ 细节必须挪到子文件'
                err = 1
            elif is_log and s > 30 * 1024:
                flag = '  [i] 历史日志（按需 Grep，不必整读）'
            rows.append((s, name, flag))
        rows.sort(reverse=True)
        for s, name, flag in rows[:a.top]:
            out.append('  %7.1f KB  %s%s' % (kb(s), name, flag))
        if len(rows) > a.top:
            out.append('  … 另有 %d 个（--top 调整）' % (len(rows) - a.top))

    print('\n'.join(out))
    return 1 if err else 0


if __name__ == '__main__':
    sys.exit(main())
