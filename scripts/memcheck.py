#!/usr/bin/env python3
"""memcheck.py —— 记忆 / skill 体积体检：**超限就报，别等用户来说拆**。

用法:
  python scripts/memcheck.py                # 默认查 本工作区 memory/ + skill
  python scripts/memcheck.py --mem <dir> --skill <dir> --limit 10240

阈值:
  MEMORY.md(自动注入)          > 8 KB  → [E] 必须拆（否则每次会话被截断）
  SKILL.md（唯一必读文件）      > 12 KB → [W] 该拆/该下沉（它替代了原先「SKILL.md+坑全量」的 33 KB 预读）
  其它 .md / engines/*.md      > limit(默认 10 KB) → [W] 按主题拆
  历史日志 YYYY-MM-DD.md        > 30 KB → [i] 仅提示（按需 Grep，不必整读）

退出码: 0 = 无 [E]/[W]; 1 = 存在待处理
★ 约定：**每作交付后固定跑一次**（见 SKILL.md §6 / MEMORY.md 收尾动作）。
"""
import os, sys, glob

DEFAULT_SKILL = os.path.expanduser('~/.workbuddy/skills/vn-custom-bytecode-text')


def kb(n):
    return n / 1024.0


def scan(root, pats, label, limit, out):
    files = []
    for pat in pats:
        files += glob.glob(os.path.join(root, pat))
    files = [f for f in files if os.path.isfile(f)]
    if not files:
        return
    out.append('\n== %s  (%s) ==' % (label, root))
    for f in sorted(files, key=os.path.getsize, reverse=True)[:40]:
        s = os.path.getsize(f)
        name = os.path.relpath(f, root)
        is_log = name[:4].isdigit() and name.endswith('.md')
        lim = 12 * 1024 if name == 'SKILL.md' else limit
        flag = ''
        if name == 'MEMORY.md' and s > 8 * 1024:
            flag = '  [E] 自动注入文件超 8 KB ⇒ 必须拆（细节挪到子文件）'
        elif is_log:
            if s > 30 * 1024:
                flag = '  [i] 历史日志 > 30 KB（按需 Grep 即可；要归档就挪进 works/<slug>.md）'
        elif s > lim:
            flag = '  [W] 超 %d KB ⇒ 按主题拆' % (lim // 1024)
        out.append('  %7.1f KB  %s%s' % (kb(s), name, flag))


def main():
    a = sys.argv[1:]
    kw = {}
    for i, x in enumerate(a):
        if x.startswith('--'):
            kw[x[2:]] = a[i + 1] if i + 1 < len(a) and not a[i + 1].startswith('--') else True
    mem = kw.get('mem') or os.path.join(os.getcwd(), '.workbuddy', 'memory')
    skill = kw.get('skill') or DEFAULT_SKILL
    limit = int(kw.get('limit', 10240))
    out = []
    scan(mem, ['*.md', 'engines/*.md', 'works/*.md', 'logs/*.md'], 'MEMORY', limit, out)
    if os.path.isdir(skill):
        scan(skill, ['SKILL.md', 'references/*.md', 'scripts/*.py'], 'SKILL', limit, out)
    print('\n'.join(out))
    bad = sum(1 for l in out if '[E]' in l or '[W]' in l)
    print('\n--- %d 处待处理 ---' % bad if bad else '\n--- 全部达标 ---')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
