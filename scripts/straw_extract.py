#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""殺し屋とストロベリー Plus —— scenario01(UnityFS) 内 TextAsset → 全文本。

记录（L1，行首命令自定界）：
    【話者】            ← 独立名字窗（剔除）
    「……本文            ← 正文（可跨 2 行，第二行以全角空格缩进）
    　……本文」          ← 上一行的排版续行 ⇒ 合并
    ＜……＞            ← 手机消息正文
    [...]  @...  ;...  ← 演出/跳转/注释，不取
"""
import os, re, sys

SRC = '_w_W1_straw/out/scenario01'
OUT = '提取结果/[NS-JP]殺し屋とストロベリー Plus.txt'
NAME_LINE = re.compile(r'^【([^】]*)】$')
NAME_INLINE = re.compile(r'^【([^】]*)】(.+)$')
SKIP0 = '[;@*#'
CMD = re.compile(r'^\[[^\]]*\]$')


def is_text(u):
    if not u:
        return False
    if u[0] in SKIP0:
        return False
    if CMD.match(u):
        return False
    return True


def parse(s):
    out = []
    lines = s.replace('\r\n', '\n').split('\n')
    i, n = 0, len(lines)
    while i < n:
        t = lines[i].strip()
        if t.startswith('【') and '】' in t:
            k = t.index('】')
            rest = t[k + 1:].strip()
            if rest.startswith(';'):          # 【名】;注释
                rest = ''
            if rest and rest[0] not in '「（＜『':   # 名后杂字（作者手误，如 【ヨダカ/？？？】s）忽略
                rest = ''
            if rest:                           # 【名】正文 同行
                out.append(rest)
                i += 1
                continue
            buf = []
            j = i + 1
            while j < n:
                u = lines[j].strip()
                if not u:
                    break
                if u[0] in '[;@*#【':
                    break
                if CMD.match(u):
                    break
                buf.append(u)
                j += 1
            if buf:
                out.append(''.join(buf))
            i = j
            continue
        i += 1
    return out


def main():
    import UnityPy
    env = UnityPy.load(SRC)
    assets = []
    for o in env.objects:
        if o.type.name != 'TextAsset':
            continue
        d = o.read()
        assets.append((d.m_Name, d.m_Script))
    assets.sort()
    allout = []
    for nm, s in assets:
        got = parse(s)
        allout.extend(got)
        print('%-22s %5d' % (nm, len(got)))
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(allout) + '\n')
    print('文件 %d / 合计 %d 行 -> %s' % (len(assets), len(allout), OUT))


if __name__ == '__main__':
    main()
