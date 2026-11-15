#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[JP]Sugar —— 全 .lsb 普查（交付前「查看所有文件」核验）。

对 VF 内**每一个** .lsb 逐一：解包 → 扫 TpWord（字数/页数/PAUSE）→ 扫选项 → 统计被本作引用次数。
输出分类：
  [ROOT]   主脚本（承载正文）
  [EXCL]   显式排除（冲突副本 / スタッフロール）
  [TEXT]   有正文但非根（子剧本或悬空，须解释为何进/不进成品）
  [EMPTY]  无任何 TpWord 正文（确认无遗漏）
  [ERR]    解包失败（须排查）
并给出「正文脚本引用闭包」与最终进成品的集合，证明无漏提。
"""
import os
import sys
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import livemaker_extract as L

EXE_DEFAULT = "_work_sugar/[JP]Sugar/Sugar.exe"
ROOT = '00000001.lsb'
EXCLUDE = [
    '00000001 (n-PC の競合コピー 2016-08-03).lsb',
    '00000081.lsb',
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exe', default=EXE_DEFAULT)
    a = ap.parse_args()

    arc = L.load(a.exe)
    # 先跑 discover 拿正文脚本集合
    story = L.discover(arc)
    for n in EXCLUDE:
        story.pop(n, None)

    # 引用闭包（从 ROOT 出发）
    order, edges, orphans = L.build_order(arc, story)
    closure = set(order)

    # ---- 全 .lsb 普查 ----
    rows = []
    n_lsb = 0
    for name in arc.names:
        if not name.lower().endswith('.lsb'):
            continue
        n_lsb += 1
        try:
            b = arc.read(name)
        except (ValueError, zlib.error) as e:
            rows.append((name, 'ERR', 0, 0, 0, 0, str(e)))
            continue
        tps = L.scan_tpwords(b)
        nchar = sum(t[3] for t in tps)
        page = sum(t[4]['page'] for t in tps)
        pause = sum(t[4]['pause'] for t in tps)
        limit = tps[-1][1] if tps else 0
        opts, dropped = L.scan_options(b, limit, L.OPT_SKIP.get(name, ()))
        refs = len(L.refs_of(b))
        rows.append((name, None, nchar, page, pause, len(opts), refs))

    # 分类
    print('=== VF 全 .lsb 普查（ver=%d, 总项=%d, .lsb=%d）===' % (arc.ver, arc.count, n_lsb))
    cls = {'ROOT': [], 'EXCL': [], 'TEXT': [], 'EMPTY': [], 'ERR': []}
    for name, kind, nchar, page, pause, nopt, refs in rows:
        if kind == 'ERR':
            cls['ERR'].append((name, nchar, page, pause, nopt, refs))
            continue
        if name in EXCLUDE:
            cls['EXCL'].append((name, nchar, page, pause, nopt, refs))
        elif name == ROOT:
            cls['ROOT'].append((name, nchar, page, pause, nopt, refs))
        elif nchar > 0:
            tag = 'IN-CLOSURE' if name in closure else 'ORPHAN'
            cls['TEXT'].append((tag, name, nchar, page, pause, nopt, refs))
        else:
            cls['EMPTY'].append((name, nchar, page, pause, nopt, refs))

    def p(clsname, items, extra=''):
        print('\n-- [%s] %s --' % (clsname, extra))
        for it in items:
            print('   ' + ' '.join(str(x) for x in it))

    p('ROOT', cls['ROOT'], '主脚本（进成品）')
    p('EXCL', cls['EXCL'], '显式排除（冲突副本 / 系统UI）')
    p('TEXT', cls['TEXT'], '有正文且非根')
    p('EMPTY', cls['EMPTY'][:50], '无任何 TpWord 正文（确认无漏提；仅列前50）' if len(cls['EMPTY']) > 50 else '无任何 TpWord 正文（确认无漏提）')
    if len(cls['EMPTY']) > 50:
        print('   ... 共 %d 个 EMPTY' % len(cls['EMPTY']))
    p('ERR', cls['ERR'], '解包失败')

    # 结论
    text_in = [it for it in cls['TEXT'] if it[0] == 'IN-CLOSURE']
    text_orphan = [it for it in cls['TEXT'] if it[0] == 'ORPHAN']
    print('\n=== 结论 ===')
    print('  进成品正文脚本: %s' % ROOT)
    print('  排除: %s' % ', '.join(EXCLUDE))
    print('  引用闭包内、有正文、非根的脚本数: %d' % len(text_in))
    for it in text_in:
        print('    [CLOSURE] %s 字=%d 页=%d 选项=%d 被引=%d' % (it[1], it[2], it[3], it[5], it[6]))
    print('  有正文但悬空(orphan)、未进成品的脚本数: %d' % len(text_orphan))
    for it in text_orphan:
        print('    [ORPHAN] %s 字=%d 页=%d 选项=%d 被引=%d（须解释）' % (it[1], it[2], it[3], it[5], it[6]))
    print('  EMPTY(无正文) .lsb 数: %d' % len(cls['EMPTY']))
    print('  ERR 数: %d' % len(cls['ERR']))


if __name__ == '__main__':
    main()
