#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[JP]alto -アルト- 文本提取驱动（Yuuki! Novel / PackageFile20）。

链路：exe → PackageFile20 目录 → 头槽 autorun.yne → LCG+XOR 解密 → WorkFile 解析 → 成品

用法：
    python scripts/alto_extract.py --src "<exe>" --out "<成品.txt>" [--work <作业目录>]

成品口径：
  一次点击＝一行；行尾 `@` 为点击标记，已去除；
  名字窗（`.WindowSet`）内容不入正文（独立名字窗，按 skill §0 剔除）；
  选项组（00 01 块）的显示文本逐条按序插入；分支标签（01 01 / 02 01）不渲染，不入成品。
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yuuki_pkg as P
from _lib import yuuki_yne as W


def load_head(d):
    """定位容器，取头槽（第 0 条内容）＝第一个脚本文件。返回 (plain, info)。"""
    info = P.scan(d)
    if not info:
        raise SystemExit('未找到 PackageFile20')
    recs = info['recs']
    dir_end = info['np0'] + P.REC * len(recs)
    lo, hi = max(0, dir_end - 0x600), min(len(d) - 8, dir_end + 0x600)
    base, hits, tot = P.guess_base(d, recs, lo, hi)
    if hits < tot * 0.9:
        raise SystemExit('数据区基准反推失败 hits=%d/%d' % (hits, tot))
    off0, size0 = recs[0][2], recs[0][3]
    blk = d[base + off0: base + off0 + size0]
    plain = P.decrypt(blk)
    return plain, {'base': base, 'hits': hits, 'total': tot,
                   'recs': len(recs), 'head_size': size0}


def build(plain):
    lines, choices = [], []
    for ev in W.iter_script(plain):
        if ev[0] == 'line':
            lines.append(ev[1])
        elif ev[0] == 'choice':
            for disp, _lab in ev[1]:
                lines.append(disp)
            choices.append([disp for disp, _ in ev[1]])
    return lines, choices


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--work')
    a = ap.parse_args()

    d = open(a.src, 'rb').read()
    plain, info = load_head(d)
    if a.work:
        os.makedirs(a.work, exist_ok=True)
        open(os.path.join(a.work, 'autorun.yne'), 'wb').write(plain)

    hdr = W.header(plain)
    lines, choices = build(plain)
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')

    print('容器磁数偏移 0x%X  记录 %d  基准 0x%X（%d/%d 魔数命中）'
          % (P.scan(d)['magic_off'], info['recs'], info['base'], info['hits'], info['total']))
    print('头槽 autorun.yne %d B → 明文 %d B；场景名「%s」头字段 %s'
          % (info['head_size'], len(plain), hdr['title'], hdr['fields']))
    print('成品行数 %d（正文 %d ＋ 选项 %d），选项组 %d 个'
          % (len(lines), len(lines) - sum(len(c) for c in choices),
             sum(len(c) for c in choices), len(choices)))
    for i, c in enumerate(choices, 1):
        print('  选项组%d: %s' % (i, ' / '.join(c)))


if __name__ == '__main__':
    main()
