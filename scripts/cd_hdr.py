#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""カスタムドライブ 条目头（0x2000 B）探针 —— 报告 §11 步骤 1 的可重跑证据。

用法：
  python scripts/cd_hdr.py hex 0 1 2          # 打印指定条目的前 256 B（u16/u32 两读）
  python scripts/cd_hdr.py fields             # 全库：逐 u16 偏移统计「每条目恒定值」
  python scripts/cd_hdr.py cand               # 候选字段：整条目恒定 + 全库取值离散且少
"""
import os, sys, struct
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cpk import CPK
from vridge_cs_customdrive import CPK as CPK_PATH

c = CPK(CPK_PATH)
E = sorted([e for e in c.entries if e['name'] and e['name'].isdigit()],
           key=lambda e: int(e['name']))
RAW = [c.raw(e) for e in E]
HDR = 0x2000


def u16s(d, n):
    return list(struct.unpack_from('<%dH' % n, d, 0))


def hexdump():
    for a in sys.argv[2:]:
        i = int(a)
        d = RAW[i]
        print('=== entry %04d  len=%d (0x%X) ===' % (i, len(d), len(d)))
        for off in range(0, 96, 16):
            chunk = d[off:off + 16]
            w16 = ' '.join('%5d' % v for v in struct.unpack_from('<8H', d, off))
            print('  %04X  %-47s  %s' % (off, d[off:off + 16].hex(' '), w16))
        print()


def fields():
    """逐 u16 偏移：该偏移在所有条目里是否恒定（用于定位「整条目恒定」的字段）。"""
    N = HDR // 2
    print('off  恒定条目数/总  最常见取值（count）')
    for off in range(N):
        vals = [struct.unpack_from('<H', d, off * 2)[0] for d in RAW]
        cnt = Counter(vals)
        top, n = cnt.most_common(1)[0]
        if n == len(vals) or n > len(vals) * 0.5:
            print('%4d(0x%03X)  %4d/%d  %d(%d)  distinct=%d'
                  % (off, off * 2, n, len(vals), top, n, len(cnt)))


def cand():
    """候选：偏移处取值「整条目内恒定」(同一条目所有框共用) —— 这里先看全库取值分布:
    取值离散、数量 ≤ 40、且高频值占有实义条目。"""
    N = HDR // 2
    rows = []
    for off in range(N):
        vals = [struct.unpack_from('<H', d, off * 2)[0] for d in RAW]
        cnt = Counter(vals)
        if 2 <= len(cnt) <= 60:
            top = cnt.most_common(4)
            rows.append((len(cnt), off, top))
    rows.sort()
    for k, off, top in rows:
        print('off %4d(0x%03X) distinct=%2d  %s' % (off, off * 2, k, top))


if __name__ == '__main__':
    {'hex': hexdump, 'fields': fields, 'cand': cand}[sys.argv[1]]()
