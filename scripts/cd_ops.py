#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""カスタムドライブ L0 opcode 统计 —— 报告 §11 步骤 2 的可重跑证据。

用法：
  python scripts/cd_ops.py freq      # opcode 频次（条目数 / token 数 / 每条目出现数分布）
  python scripts/cd_ops.py once      # 「每条目恰好 1 次 且 操作数∈小集合」的 opcode（候选＝相手役 id）
  python scripts/cd_ops.py op <hex>  # 单个 opcode 的操作数分布 + 首现上下文
"""
import os, sys, struct
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cpk import CPK
from vridge_psp_run import toks, words_to_text
from vridge_cs_customdrive import (CPK as CPK_PATH, CHARSET, SPECIAL, CAST,
                                   PROTAG_GIVEN)

c = CPK(CPK_PATH)
E = sorted([e for e in c.entries if e['name'] and e['name'].isdigit()],
           key=lambda e: int(e['name']))
TK = [toks(c.raw(e)) for e in E]


def freq():
    ent = Counter()
    tok = Counter()
    for tk in TK:
        seen = set()
        for op, _ in tk:
            tok[op] += 1
            if op not in seen:
                seen.add(op)
                ent[op] += 1
    print('entries %d' % len(TK))
    print(' opcode  entries  tokens')
    for op, n in tok.most_common():
        if n < 3:
            break
        print('  %04X  %6d  %7d' % (op, ent[op], n))


def once():
    """每条目出现次数分布 + 操作数取值集合。"""
    stat = defaultdict(lambda: {'percnt': Counter(), 'oper': Counter(), 'ents': 0})
    for tk in TK:
        cnt = Counter(op for op, _ in tk)
        for op, n in cnt.items():
            s = stat[op]
            s['ents'] += 1
            s['percnt'][n] += 1
    for tk in TK:
        for op, run in tk:
            stat[op]['oper'].update(run)
    rows = []
    for op, s in stat.items():
        if s['ents'] < 20:
            continue
        one = s['percnt'][1] / max(1, sum(s['percnt'].values()))
        dis = len(s['oper'])
        rows.append((dis, -one, op, s))
    print('候选：操作数取值少（distinct）且「每条目 1 次」占比高')
    print(' opcode  entries  1x占比  operand distinct  最常见操作数')
    shown = 0
    for dis, no, op, s in sorted(rows):
        if dis > 40 or -no < 0.5:
            continue
        top = ', '.join('%d(%d)' % (v, n) for v, n in s['oper'].most_common(6))
        print('  %04X  %6d  %5.2f  %8d  %s' % (op, s['ents'], -no, dis, top))
        shown += 1
    print('(共 %d 项)' % shown)


def op():
    o = int(sys.argv[2], 16)
    oper = Counter()
    ent = 0
    for i, tk in enumerate(TK):
        hit = [(k, run) for k, (op_, run) in enumerate(tk) if op_ == o]
        if not hit:
            continue
        ent += 1
        for _, run in hit:
            oper.update(run)
    print('%04X: entries %d, operand distinct %d' % (o, ent, len(oper)))
    print(' ', oper.most_common(60))


if __name__ == '__main__':
    {'freq': freq, 'once': once, 'op': op}[sys.argv[1]]()
