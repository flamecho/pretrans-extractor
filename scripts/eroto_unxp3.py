# -*- coding: utf-8 -*-
"""XP3 脚本层解包（LiveMaker/KiriKiri 通用）：解出 .ks/.tjs/.txt/.sli/.asd 并列出全部成员分类。

用法:
    python eroto_unxp3.py <data.xp3> [输出目录]
    输出目录默认 <xp3 同目录>/ks

（原 _work_eroto/unxp3.py，2026-11-10 迁入 tools 并改为 argv 式，供清理工作目录后复跑）
"""
import sys
import os
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xp3 import XP3

KEEP = ('.ks', '.tjs', '.txt', '.sli', '.asd')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) >= 3 else os.path.join(os.path.dirname(os.path.abspath(src)), 'ks')
    x = XP3(src)
    os.makedirs(out, exist_ok=True)

    exts = collections.Counter()
    kept = []
    for n in sorted(x.files):
        e = os.path.splitext(n)[1].lower()
        exts[e] += 1
        if e in KEEP:
            data = x.read(n)
            # 归档内可能有超长「protected archive」警告名 ⇒ 截断到可落盘长度
            parts = n.replace('/', os.sep).split(os.sep)
            parts = [(p[:120] if len(p) > 120 else p) for p in parts]
            p = os.path.join(out, *parts)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'wb').write(data)
            kept.append((n[:100], len(data)))
    print('成员总数', len(x.files))
    for e, c in sorted(exts.items(), key=lambda kv: -kv[1]):
        print('  %-8s %d' % (e, c))
    print('\n解出脚本层 %d 个 → %s' % (len(kept), out))
    for n, sz in kept:
        print('  %-46s %8d' % (n, sz))
    return 0


if __name__ == '__main__':
    sys.exit(main())
