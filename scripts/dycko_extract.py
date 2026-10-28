#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[PC-JP] DYNAMIC CHORD feat.KYOHSO Append Disc（honeybee black / ASGARD / PC 2016）

ASGARD 自研 AdvHD（.wsc 字节码）链路；ISO 直读，不落整盘。

链路
  ISO9660（scripts/iso9660.py 直读）→ RIO.ARC（4,708,724 B）
  → Will/AdvHD「ext-group」容器：u32 groupCount | [ext 4B][count u32][tableOff u32]
     条目 21 B：[name 13B][size u32][offset u32]
  → 每字节 rotl_8(c,6) → ws2 字节码
  → advhd.walk：0x41 旁白 / 0x42 名+台词 / 0x02 选项

与 apple-polisher（同系列 PC 前作）的差异
  · 容器：本条为 Will ext-group（前作为自研 count/name-UTF16 变体）
  · 文本 op：本条 0x41/0x42（前作 0x14/char 指令）
  · 0x4B 参数长 = 20（前作 / Double Score 同为 20，表内 16 会失步）
  · 主角名无 <@FIRNAME> 宏，正文直接写字面「霧下」

路径顺序（EVEXEC 事件表 ＋ KKYO_16 分岐引用，两处一致）
  KKYO（共通）→ KYOR+EYOR（依都）→ KTOK+ETOK（時明）
  → KYUU+EYYU（優）→ KSNO+ESNO（篠宗）→ KOMAKE（おまけ）

用法: python scripts/dycko_extract.py [--src RIO.ARC] [--out xx.txt] [--stats]
"""
import argparse
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import advhd

HOME = os.environ.get('VNTRANS_HOME', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(HOME, '_work_dycko/x/RIO.ARC')
OUT = os.path.join(HOME, '提取结果/[PC-JP]DYNAMIC CHORD feat.KYOHSO Append Disc.txt')

advhd.GENERIC[0x4B] = 20          # 本作实测；16（表内默认）会失步

STORY = re.compile(r'^(KKYO|KYOR|KSNO|KTOK|KYUU|EYOR|ESNO|ETOK|EYUU|KOMAKE)_?(.*)$')
MAIN_ROUTES = ['KKYO', 'KYOR', 'KTOK', 'KYUU', 'KSNO']
ENCORE_ROUTES = ['EYOR', 'ETOK', 'EYUU', 'ESNO']


def natkey(nm):
    """KKYO_07 / KKYO_07CZ / KKYO_END1 → 数字优先，END 类收在该路线末。"""
    rest = STORY.match(nm).group(2)
    m = re.match(r'^(\d+)([A-Z]*)$', rest)
    if m:
        return (0, int(m.group(1)), m.group(2), '')
    return (1, 0, '', rest)


def order_names(names):
    groups = {}
    for nm in names:
        m = STORY.match(nm)
        if m:
            groups.setdefault(m.group(1), []).append(nm)
    seq = []
    for r in MAIN_ROUTES + ENCORE_ROUTES + ['KOMAKE']:
        seq += sorted(groups.get(r, []), key=natkey)
    return seq


def clean(t):
    """富文本 / ruby / 软换行 → 纯文本。"""
    t = re.sub(r'%[A-Z]{1,3}', '', t)                 # %K %P %O %LC %LR …
    t = re.sub(r'[\ue000-\uf8ff]', '', t)             # 内联图标（PUA 字形槽）
    # ruby 注音 {漢字:かな} → 只留基底；基底限定不含 = " ' 与空白，避免误吃脚本式
    t = re.sub(r'\{([^{}:：="\'\s]+)[:：][^{}]*\}', r'\1', t)
    t = re.sub(r'(?:\\n)+[ \u3000]*', '', t)          # 框内软换行 ＋ 续行缩进
    t = t.replace('\\n', '')
    t = re.sub(r'[\x00-\x08\x0b-\x1f]', '', t)
    return t.strip(' \u3000\t')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=SRC)
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--stats', action='store_true')
    a = ap.parse_args()

    d = open(a.src, 'rb').read()
    ents = advhd.parse_arc(d)
    seq = order_names(list(ents))

    lines, per, empty = [], [], 0
    for nm in seq:
        _e, ln, so = ents[nm]
        b = advhd.decrypt(d[so:so + ln])
        n0 = len(lines)
        for op, ss in advhd.walk(b):
            if op == 0x02:
                for s1, _s2 in ss:
                    t = clean(s1.decode('cp932', 'replace'))
                    if t:
                        lines.append(t)
                continue
            if op not in (0x41, 0x42):
                continue
            t = clean((ss[0] if op == 0x41 else ss[1]).decode('cp932', 'replace'))
            if t:
                lines.append(t)
            else:
                empty += 1
        per.append((nm, len(lines) - n0))

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')

    if a.stats:
        print('scripts %d   lines %d   dropped-empty %d' % (len(seq), len(lines), empty))
        for nm, c in per:
            print('  %-12s %4d' % (nm, c))
    print('->', a.out, len(lines), '行')


if __name__ == '__main__':
    main()
