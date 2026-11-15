#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[NS-JP]恋してしまった星の王子 ～誓願院編～ 文本提取（Bezel Engine / SCNE / scb_）。

用法：
  python extract.py                 # 生成成品到 提取结果/
  python extract.py --dump          # 只统计
"""
import struct, os, re, sys, json, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zstandard
from _lib.bezel_scb_lib import asst_entries, member, parse_scb, clean

BEA = os.path.join(VNTRANS_HOME, "还没做/[NS-JP]恋してしまった星の王子 ～誓願院編～/romfs/Archive/script.nxonnx32.bea")
OUT = os.path.join(VNTRANS_HOME, "提取结果/[NS-JP]恋してしまった星の王子 ～誓願院編～.txt")
DUMP = os.path.join(VNTRANS_HOME, "_work_hoshioji/dump.json")

T_OPEN, T_NAME, T_TEXT, T_CHOICE = 0x05, 0x0B, 0x0C, 0x13
T_CLOSE = (0x11, 0x12)


def run():
    raw = open(BEA, 'rb').read()
    ents = asst_entries(raw)
    table = {e[0]: e for e in ents}
    ja = sorted(k for k in table if '/ja/' in k)
    en = sorted(k for k in table if '/en/' in k)
    print('[i] ASST0 资源 %d（ja %d / en %d）' % (len(ents), len(ja), len(en)))

    lines = []
    per_file = collections.OrderedDict()
    n_empty_boxes = 0
    n_choice = 0
    n_box = 0
    box_sizes = collections.Counter()
    for nm in ja:
        _, csize, usize, doff = table[nm]
        ops, strs = parse_scb(member(raw, csize, usize, doff))
        n0 = len(lines)
        cur_name, cur_text, in_box, texts = '', '', False, 0
        for (o, t, a) in ops:
            if t == T_OPEN:
                in_box, cur_name, cur_text, texts = True, '', '', 0
                n_box += 1
            elif t == T_NAME and in_box:
                cur_name = strs[a[0]] if a and a[0] < len(strs) else ''
            elif t == T_TEXT and in_box:
                cur_text = strs[a[0]] if a and a[0] < len(strs) else ''
                texts += 1
            elif t in T_CLOSE and in_box:
                box_sizes[texts] += 1
                txt = clean(cur_text)
                if txt:
                    nmz = clean(cur_name)
                    lines.append((nmz + txt) if nmz else txt)
                else:
                    n_empty_boxes += 1
                in_box = False
            elif t == T_CHOICE:
                for k in range(0, len(a) - 2, 3):
                    idx = a[k]
                    if idx < len(strs):
                        s = clean(strs[idx])
                        if s:
                            lines.append(s)
                            n_choice += 1
        per_file[nm] = len(lines) - n0

    print('[i] 文本框 %d；正文行 %d；空框 %d；选项 %d' % (n_box, len(lines) - n_choice, n_empty_boxes, n_choice))
    print('[i] 每框正文 op 数分布:', dict(sorted(box_sizes.items())))
    print('[i] 合计 %d 行' % len(lines))

    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('[i] -> %s' % OUT)
    json.dump({'per_file': per_file, 'boxes': n_box, 'empty_boxes': n_empty_boxes,
               'choice': n_choice, 'lines': len(lines), 'ja': len(ja), 'en': len(en),
               'box_sizes': dict(box_sizes)},
              open(DUMP, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    run()
