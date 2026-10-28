#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""グリム・ザ・バウンティハンター（PSP / QuinRose / KiriKiri KAG .ks）文本提取。

链路：ISO9660 → USRDIR/DATA/DATA0.cpk（CRI CPK）→ 114 个明文 .ks
     → [message window=..]..[/message] = 一次点击 ⇒ 一行（[br]/物理换行 = 框内软换行 ⇒ 合并）
     → [select word=..] = 选项；[select name=..] = 图片无字选项 ⇒ 跳过
     → [cg file="*_textNN*.png"] + [backlog]…[/backlog] = 上屏扉文/世界観説明 ⇒ 同 NN 合并一行
"""
import glob
import os
import re
import sys

FIRST = 'リーザ'      # 主角名（vndb/ymgal: リーザ＝ベルネット）
FAMILY = 'ベルネット'

# 收录顺序：序章 → OP → 各线路（chapter 1→15）→ 共通幕間 → サブ → ミニゲーム → 结局
ROUTE = ['ado', 'bre', 'hag', 'jul', 'rap']
END = ['hei_end.ks', 'kro_end.ks', 'tru_end.ks', 'wid_end.ks']
COM = ['com05.ks', 'com07.ks', 'com09.ks', 'com_sub.ks']
SUB = ['sub01.ks', 'sub02.ks', 'sub03.ks']
MINI = ['mini_step3_start.ks', 'mini_step3_select.ks', 'mini_step3_result.ks',
        'mini_step1_result.ks', 'mini_step2_result.ks',
        'mini_step4_start.ks', 'mini_step4_result.ks']

# 系统提示（OP スキップ案内／名前入力の説明）⇒ 整段剔除
SYS_SPANS = {'prologue.ks': [('*prologue_02', '*op_skip_select01')]}
SYS_LINES = {'名前、苗字は共に７文字までです。'}


def order():
    seq = ['prologue.ks', 'op01.ks', 'op01_2.ks', 'op02.ks', 'op03.ks']
    for r in ROUTE:
        seq += ['%s%02d.ks' % (r, i) for i in range(1, 16)]
    seq += COM + SUB + MINI + END
    return seq


BLOCK = re.compile(r'\[message\b([^\]]*)\](.*?)\[/message\]', re.S)
SELECT = re.compile(r'\[select\b([^\]]*)\]')
BACKLOG = re.compile(r'\[cg file="([^"]*_text(\d+)[^"]*)"[^\]]*\]\s*'
                     r'\[backlog[^\]]*\](.*?)\[/backlog\]', re.S)


def fix_body(body):
    s = body
    s = s.replace('[br]', '')
    s = re.sub(r'\[/f\]', '', s)
    s = re.sub(r'\[f\b[^\]]*\]', '', s)
    s = re.sub(r'\[print\s+value="firstname"\]', FIRST, s)
    s = re.sub(r'\[print\s+value="familyname"\]', FAMILY, s)
    left = re.findall(r'\[[^\]]*\]', s)
    if left:
        sys.stderr.write('LEFTOVER %r\n' % left[:3])
    s = re.sub(r'\[[^\]]*\]', '', s)
    parts = [p.strip(' \t\u3000\r') for p in s.split('\n')]
    return ''.join(parts)


def main(src, out):
    seq = order()
    have = {os.path.basename(p) for p in glob.glob(os.path.join(src, '*.ks'))}
    miss = [f for f in seq if f not in have]
    extra = sorted(have - set(seq))
    lines, stat = [], {}
    for fn in seq:
        path = os.path.join(src, fn)
        if not os.path.exists(path):
            continue
        t = open(path, 'rb').read().decode('cp932')
        # KAG 注释行（行首 ;）= 已禁用的旧稿，不得当正文
        t = '\n'.join(l for l in t.split('\n') if not l.lstrip().startswith(';'))
        spans = []
        for a, b in SYS_SPANS.get(fn, []):
            ma = re.search(r'^' + re.escape(a), t, re.M)
            mb = re.search(r'^' + re.escape(b), t, re.M)
            if ma and mb and mb.start() > ma.start():
                spans.append((ma.start(), mb.start()))

        def skipped(p):
            return any(a <= p < b for a, b in spans)

        ev = []
        for m in BLOCK.finditer(t):
            if not skipped(m.start()):
                ev.append((m.start(), 0, fix_body(m.group(2))))
        for m in SELECT.finditer(t):
            if skipped(m.start()):
                continue
            w = re.search(r'word="([^"]*)"', m.group(1))
            if w:                                   # name="sel_*.png" = 图片无字选项
                ev.append((m.start(), 1, w.group(1).strip()))
        # 扉文：同一 *_textNN 的连续 backlog 合并
        groups, cur = [], None
        for m in BACKLOG.finditer(t):
            if skipped(m.start()):
                continue
            s = fix_body(m.group(3))
            if not s or s == '　':
                continue
            key = m.group(2)
            if cur and cur[0] == key:
                cur[2].append(s)
            else:
                cur = [key, m.start(), [s]]
                groups.append(cur)
        for _, pos, parts in groups:
            ev.append((pos, 2, ''.join(parts)))
        ev.sort()
        n = 0
        for _, _, s in ev:
            if not s or s in SYS_LINES:
                continue
            lines.append(s)
            n += 1
        stat[fn] = n
    data = '\n'.join(lines) + '\n'
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write(data)
    print('files', len(stat), 'lines', len(lines))
    print('missing', miss)
    print('extra', extra)
    print('check', sum(stat.values()) == len(lines))
    for k, v in stat.items():
        if v == 0:
            print('EMPTY', k)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
