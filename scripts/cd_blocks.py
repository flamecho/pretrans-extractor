#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""カスタムドライブ：用「单男角条目块」反查 相手役 id 字段 —— 报告 §11 步骤 2 的可重跑证据。

思路（可证伪）：
  570 个条目只有 1 个具名角色说话 ⇒ 该条目相手役必为他（排除法，无概率）。
  这些条目按条目号连成若干「块」（连续同人）。若存在某个 opcode 的操作数
  ＝ 相手役 id，则它必须在**同一块内恒定**、且**不同人不同值**。
  反之，只要某 opcode 在同块内抖动 ⇒ 该 opcode 不是相手役字段（直接证伪）。

用法：python scripts/cd_partner.py 见 cd_blocks.py
  python scripts/cd_blocks.py blocks     # 打印块表
  python scripts/cd_blocks.py scan       # 逐 opcode 检验「块内恒定 + 跨块可区分」
"""
import os, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cpk import CPK
from vridge_psp_run import toks, plate_spans
from vridge_cs_customdrive import (CPK as CPK_PATH, CHARSET, SPECIAL, CAST,
                                   PROTAG_GIVEN)

c = CPK(CPK_PATH)
E = sorted([e for e in c.entries if e['name'] and e['name'].isdigit()],
           key=lambda e: int(e['name']))
TK = [toks(c.raw(e)) for e in E]


def entry_males():
    out = []
    for tk in TK:
        starts, spks = plate_spans(tk, CHARSET, SPECIAL, PROTAG_GIVEN)
        out.append({s for s in spks if s in CAST})
    return out


MALES = entry_males()


def blocks():
    """连续「单男角且同一人」的条目块（长度≥2）。"""
    res = []
    i = 0
    while i < len(MALES):
        if len(MALES[i]) == 1:
            j = i
            who = next(iter(MALES[i]))
            while j + 1 < len(MALES) and MALES[j + 1] == {who}:
                j += 1
            if j > i:
                res.append((i, j, who))
            i = j + 1
        else:
            i += 1
    return res


def scan():
    bl = blocks()
    print('块数 %d，覆盖条目 %d' % (len(bl), sum(b - a + 1 for a, b, _ in bl)))
    print('%-8s %-5s %-10s' % ('range', 'len', 'who'))
    for a, b, w in bl:
        print('%-8s %-5d %-10s' % ('%04d-%04d' % (a, b), b - a + 1, w))
    # 每块的 (opcode, 出现次数) → 操作数集合
    rows = []
    for op in set(o for tk in TK for o, _ in tk):
        ok_blocks = 0
        mapping = {}
        bad = []
        for a, b, w in bl:
            vals = set()
            for i in range(a, b + 1):
                occ = [run for o, run in TK[i] if o == op]
                for run in occ:
                    vals.add(tuple(run))
            if len(vals) == 1:
                ok_blocks += 1
                mapping.setdefault(w, set()).add(next(iter(vals)))
            else:
                bad.append((a, b, w, len(vals)))
        # 跨块：同一人是否只对应同一值
        conflict = {k: v for k, v in mapping.items() if len(v) > 1}
        rows.append((ok_blocks, op, conflict, mapping, bad))
    rows.sort(key=lambda r: (-r[0], len(r[2])))
    print('\n块内恒定的 opcode（越多越可能＝相手役 id）：')
    for ok, op, conflict, mapping, bad in rows[:25]:
        tag = 'OK ' if not conflict else 'CONFLICT'
        print('  %04X  恒定块 %2d/%d  %s' % (op, ok, len(bl), tag))
        if ok >= len(bl) * 0.8:
            for w, vs in sorted(mapping.items()):
                ex = sorted(vs)[0]
                print('      %-10s %s' % (w, list(ex)[:6]))


if __name__ == '__main__':
    {'blocks': lambda: [print('%04d-%04d %s' % (a, b, w)) for a, b, w in blocks()],
     'scan': scan}[sys.argv[1]]()
