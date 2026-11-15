#!/usr/bin/env python3
"""[JP]Seiyuu Danshi! 文本抽取驱动（Ren'Py 7.2.2）

用法：python scripts/seiyuu_extract.py <game_dir> <out_txt>
"""
import sys
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
from pathlib import Path

sys.path.insert(0, os.path.join(VNTRANS_HOME, "tools"))
import renpy_text as R

# 文本载体（L1 依据：函数签名见 game/messages.rpy / game/socialmedia.rpy）
CARRIERS = {
    'add_message': 2,   # add_message(subject, sender, body)   ← 第 3 参
    'add_tweet': 1,     # add_tweet(avatar, content, date)     ← 第 2 参
}
PURE_VARS = ('line',)   # 试镜台词：$ line = "…" 赋值处输出，checker 里的 mc "[line]" 不重复出

INTERP = {
    'name': 'Haato',    # main.rpy:1174 renpy.input(..., default='Haato')
}

# 整文件排除：testing.rpy 是开发者跳转菜单（886 条调试快跳，无正文，仅被注释掉的 jump 引用）
EXCLUDE_FILES = {'testing.rpy'}
# 块排除：同文件内的调试作弊 label（backtoselection 的 1 句 + 2 选项是调试菜单项）
SKIP_LABELS = ('cheat_dirtytalk', 'cheat_foreplaymode', 'backtoselection')


def main():
    game = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    files = sorted(p for p in game.rglob('*.rpy')
                   if 'tl' not in p.parts and p.name not in EXCLUDE_FILES)

    chars = set()
    for f in files:
        s = f.read_text(encoding='utf-8-sig', errors='replace')
        for m in re.finditer(r'^\s*define\s+(\w+)\s*=\s*Character\(', s, re.M):
            chars.add(m.group(1))

    lines, stats, slots, unres_calls, p = R.extract(
        files, chars, INTERP, carriers=CARRIERS, pure_vars=PURE_VARS,
        skip_labels=SKIP_LABELS)

    bad = [x for x in lines if not x.strip()]
    out_path.write_text('\ufeff' + '\n'.join(lines) + '\n', encoding='utf-8', newline='\n')

    log = []
    log.append(f'files={len(files)} chars={len(chars)}')
    log.append(f'stmts={len(p.stmts)} dyn_unresolved={len(p.dyn_unresolved)}')
    log.append(f'stats={stats}')
    log.append(f'empty_lines={len(bad)}')
    log.append('slot_log=' + repr(sorted(slots.items(), key=lambda kv: -kv[1])))
    log.append('unresolved_calls:')
    for f, ln, txt in unres_calls:
        log.append(f'  {f}:{ln} {txt}')
    log.append('dyn_unresolved:')
    for loc, txt in p.dyn_unresolved:
        log.append(f'  {loc} {txt}')
    text = '\n'.join(log)
    Path('extract2.log').write_text(text + '\n', encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()
