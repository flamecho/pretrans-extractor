#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KLAP!! STCM2L 单段 opcode 追踪：看「一行多句」在代码层是怎么分隔的。

用法: python scripts/klap_trace.py <SCRIPT目录> <关键词> [文件过滤]
输出: 命中文件 + 该段所有指令（含未识别 op）+ 全库「正文片段之间夹的 op」统计
"""
import sys, os, glob, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sympathy_extract import readrec
from klap_extract import walk, BODY, NAME, CLICK, CHOICE, JP

OPNAME = {0x1348C: 'BODY', 0x13BF8: 'NAME', 0x1F4: 'CLICK', 0x15524: 'CHOICE',
          0x6AE8: 'flag', 0x6108: 'cond/switch', 0x64D8: 'cond', 0x62F0: 'love',
          0x18C8: 'jump', 0x6: 'goto', 0x3: 'Mif', 0x11: 'op11', 0x12: 'op12', 0x0: 'end'}


def trace(scripts, key):
    between = collections.Counter()          # 正文片段之间夹的 op（同一框内）
    for src in scripts:
        for fn in sorted(glob.glob(os.path.join(src, '*.DAT'))):
            d = open(fn, 'rb').read()
            ops = list(walk(d))
            hit = [i for i, (o, op, sl) in enumerate(ops)
                   if op in BODY and sl and sl[0] and key in sl[0]]
            if hit:
                print('=== %s  命中 op#%s / 共 %d 条指令' % (os.path.basename(fn), hit, len(ops)))
                for h in hit:
                    lo, hi = max(0, h - 12), min(len(ops), h + 14)
                    for i in range(lo, hi):
                        o, op, sl = ops[i]
                        nm = OPNAME.get(op, 'op_0x%X' % op)
                        txt = ' ｜ '.join((s or '∅')[:60] for s in sl[:4])
                        print('  %s #%-5d 0x%08X(%s) argc=%d  %s'
                              % ('→' if i == h else ' ', i, op, nm, len(sl), txt))
                    print('  ---')
            # 统计：相邻两条 BODY 之间夹的 op 序列
            for i in range(len(ops) - 1):
                if ops[i][1] not in BODY:
                    continue
                j = i + 1
                if j < len(ops) and ops[j][1] in BODY:
                    between['直接相邻(无夹层)'] += 1
                else:
                    chain = []
                    while j < len(ops) and ops[j][1] not in BODY and len(chain) < 4:
                        chain.append(OPNAME.get(ops[j][1], 'op_0x%X' % ops[j][1]))
                        if ops[j][1] in CLICK:
                            break
                        j += 1
                    between[' + '.join(chain)] += 1
    print('\n=== 全库「正文片段之后紧跟什么」统计（前 15）')
    for k, v in between.most_common(15):
        print('  %6d  %s' % (v, k))


if __name__ == '__main__':
    trace(sys.argv[1].split(','), sys.argv[2])
