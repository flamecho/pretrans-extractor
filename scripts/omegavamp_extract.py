#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""オメガヴァンパイア (NS) SCRIPT.PAK → 全文本（一行＝一次点击）。

记录形状（实测，L1 自定界：长度前缀＋00 00 终止符，并以 op 位置交叉验证）：
  消息： 21 03 | A(u16 行号) | B(u16 段内序号) | C(u16 全局计数器) | n(u16 字符数) | n×UTF-16LE | 00 00
  选项： 24 01 | 行号 | 76 17 | 3×u16 | n(u16) | n×UTF-16LE | 00 00 ，串内 '$d' 分隔各选项
  名字： 串首 '`' + 名字 + '@' + 正文（引擎把名字单列到名字窗）
  注音： $[本体$/読み$] → 取本体
"""
import struct, os, re, sys

SRC = '_work_omegavamp/romfs/SCRIPT.PAK'
OUT = '提取结果/[NS-JP]オメガヴァンパイア.txt'
RUBY = re.compile(r'\$\[([^$]*)\$/?[^$]*\$\]')


def clean_ok(s):
    if not s:
        return False
    for c in s:
        o = ord(c)
        if o < 0x20 and c != '\n':
            return False
        if 0xe000 <= o <= 0xf8ff or o in (0xfffd, 0xfeff):
            return False
    return True


def scan(d):
    N = len(d)
    ms, ch = [], []
    for p in range(0x290, N - 4):
        n = struct.unpack('<H', d[p:p + 2])[0]
        if not (1 <= n <= 600) or p + 2 + 2 * n + 2 > N:
            continue
        if d[p + 2 + 2 * n:p + 4 + 2 * n] != b'\x00\x00':
            continue
        ts = p + 2
        try:
            s = d[ts:ts + 2 * n].decode('utf-16le')
        except Exception:
            continue
        if not clean_ok(s):
            continue
        kind = None
        if ts >= 10 and d[ts - 10:ts - 8] == b'\x21\x03':
            A, B, C = struct.unpack('<3H', d[ts - 8:ts - 2])
            kind = ('m', A, B, C)
        elif ts >= 14 and d[ts - 14:ts - 12] == b'\x24\x01' and d[ts - 10:ts - 8] == b'\x76\x17':
            kind = ('c',)
        if not kind:
            continue
        rec = (ts, ts + 2 * n, kind, s)
        if kind[0] == 'm':
            ms.append(rec)
        else:
            ch.append(rec)
    # 同一位置可能被重叠匹配（串内含 21 03 假头）⇒ 按位置贪心去重
    allrec = sorted(ms + ch)
    keep, end = [], 0
    for ts, te, kind, s in allrec:
        if ts < end:
            continue
        keep.append((ts, te, kind, s))
        end = te
    ms = [r for r in keep if r[2][0] == 'm']
    ch = [r for r in keep if r[2][0] == 'c']
    return ms, ch


def clean(s):
    if s.startswith('`') and '@' in s:
        s = s[s.index('@') + 1:]
    s = RUBY.sub(r'\1', s)
    return s.replace('\n', '').replace('\r', '')


def main():
    d = open(SRC, 'rb').read()
    ms, ch = scan(d)
    items = [(r[0], 0, clean(r[3])) for r in ms]
    for r in ch:
        for k, opt in enumerate(r[3].split('$d')):
            items.append((r[0], 1 + k, clean(opt)))
    items.sort(key=lambda x: (x[0], x[1]))
    lines = [t for _, _, t in items if t.strip()]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(lines) + '\n')

    bad = [t for t in lines if any(ord(c) < 0x20 or c in '$`@' for c in t)]
    print('msgs %d  choice_rec %d  opts %d  lines %d'
          % (len(ms), len(ch), sum(len(r[3].split('$d')) for r in ch), len(lines)))
    print('residual_macro', len(bad), bad[:3])
    print('maxlen', max(len(t) for t in lines))


if __name__ == '__main__':
    main()
