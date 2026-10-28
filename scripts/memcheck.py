#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""memcheck.py —— 目录体检：只报「真会出问题」的体积，其余仅列大小。

**分册不再按体积判**（2026-10-26 用户取消 10 KB / 12 KB 硬线）。
理由：分册该多大由**主题**决定，不由字节数决定。按字节硬切会把同一主题拆散
——曾经的「late-1…late-6」就是这么切出来的，光看文件名读不出内容，
查一个坑要连开六册。判断该不该拆的唯一标准是「**读者是否需要同时看这两段**」，不是 KB。

保留的两条体积判断都有技术原因，与编辑偏好无关：
  MEMORY.md   > 8 KB  → [E]  自动注入会话上下文，超了会被截断（信息真的会丢）
  历史日志    > 30 KB → [i]  只提示；按需 `Grep` 命中段即可，不必整读

用法:
  python scripts/memcheck.py                    # 查本工作区 memory/ + 本 skill
  python scripts/memcheck.py --mem DIR --skill DIR --top 40
退出码: 0 = 无 [E]；1 = MEMORY.md 超 8 KB
"""
import argparse
import glob
import os
import sys

DEFAULT_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
            (a.mem, '工作区记忆', ['*.md', 'engines/*.md']),
            (a.skill, 'skill', ['SKILL.md', 'references/*.md', 'references/*/*.md'])):
        files = []
        for pat in pats:
            files += glob.glob(os.path.join(root, pat))
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
