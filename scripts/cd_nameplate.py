#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""カスタムドライブ 名札（说话人）核验探针 —— 报告 §10 的可重跑证据。

用法：
  python scripts/cd_nameplate.py table    # 名札整表（名/枚数/性格变体），与 vndb cast 对照
  python scripts/cd_nameplate.py ff0c     # FF0C 分级：按框说话人 + 填值分布 + 占位数

结构（L0）：FFF0 <槽位号 u16> <名字码…>；槽位号每条目从 0 递增，不是字符。
           len(run)<=1 且下一 op＝FFE6/FFE7 ⇒ 主角（名牌走可改名宏）。
"""
import os, sys, re
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cpk import CPK
from vridge_psp_run import toks, words_to_text, plate_spans, plan_ff0c
from vridge_cs_customdrive import CHARSET, SPECIAL, CAST, PROTAG_GIVEN, FF0C_FALLBACK
from vridge_cs_customdrive import CPK as CPK_PATH

c = CPK(CPK_PATH)
entries = sorted([e for e in c.entries if e['name'] and e['name'].isdigit()],
                 key=lambda e: int(e['name']))


def table():
    nm, var = Counter(), Counter()
    protag = blank = 0
    for e in entries:
        tk = toks(c.raw(e))
        for k, (op, run) in enumerate(tk):
            if op != 0xFFF0:
                continue
            nxt = tk[k + 1][0] if k + 1 < len(tk) else 0
            if len(run) <= 1:
                if nxt == 0xFFE6:
                    protag += 1
                else:
                    blank += 1
                continue
            s = words_to_text(run[1:], CHARSET, SPECIAL)
            m = re.match(r'^([^（]+)（(.*)）$', s)
            if m:
                nm[m.group(1)] += 1
                var[(m.group(1), m.group(2))] += 1
            else:
                nm[s] += 1
    print('名札 %d 枚 ＝ 主角宏 %d ＋ 具名 %d（%d 种）＋ 无名札 %d'
          % (protag + blank + sum(nm.values()), protag, sum(nm.values()), len(nm), blank))
    for s, n in nm.most_common(200):
        if n < 5:
            break
        v = [x for (a, _), x in var.items() if a == s]
        print('%6d  %-12s 变体%d%s  %s' % (n, s, len(v), '　' if v else '　',
                                           'vndb' if s in CAST else ''))


def ff0c():
    tier = Counter()
    fill = Counter()
    for e in entries:
        tk = toks(c.raw(e))
        plan = plan_ff0c(tk, CHARSET, SPECIAL, CAST, PROTAG_GIVEN, FF0C_FALLBACK)
        if not plan:
            continue
        starts, spks = plate_spans(tk, CHARSET, SPECIAL, PROTAG_GIVEN)
        mcnt = Counter(s for s in spks if s in CAST)
        import bisect
        for k, rep in plan.items():
            b = bisect.bisect_left(starts, k) - 1
            spk = spks[b] if 0 <= b < len(spks) else None
            if rep == FF0C_FALLBACK:
                tier['③ 占位（多男角/无男角）'] += 1
            elif spk in CAST:
                tier['① 男角说话→主角名'] += 1
            else:
                tier['② 单男角条目·排除法'] += 1
            fill[rep] += 1
    print('FF0C token 合计 %d' % sum(tier.values()))
    for k, v in tier.most_common():
        print('  %-26s %5d' % (k, v))
    print('填值分布：', fill.most_common(12))


if __name__ == '__main__':
    {'table': table, 'ff0c': ff0c}[sys.argv[1] if len(sys.argv) > 1 else 'table']()
