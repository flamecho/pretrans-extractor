#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[PC-JP]君がため、恋し乱れし月の華。 KiriKiri RAT（linemode=free）全文本提取。

L0 判据（引擎源码，非统计）：
  scenario/macro.ks 的 [initscene] 里 [linemode mode=free]
  system/MainWindow.tjs parseR() 的 case LINEMODE_FREE：
    空行 ⇒ parseP（页断＋一次点击 ⇒ 文本框界）；连续非空行 ⇒ 不产生页断
    （emptyCheck 只补 [r] 框内换行）⇒ 框内各行合并。
  名字：行首【名】 ⇒ parseCh 产出 addParseTag("dispname")＝独立名字窗 ⇒ 剔除。
  余話：scenario/ss_*.ks（main/yowalist.csv 的 popup 正文）⇒ 收。
  排除：scenario/replay（回想副本，逐行与正本重复 98–100%）、sysscn/main/uipsd（系统 UI）、
        macro/start/parsermacro/gototitle/test_manpu。
  patch：patch2.xp3 的根目录同名 .ks（53 个）覆盖本体（官方 v1.02 错字修正）。

双版：本作 [l]/[p]/[nowait]/[waitclick] 全 0（无框内多次点击）；
  跨框断引号/括号（前框开未收、紧邻后框正好收）0 组 ⇒ 单版，一框一行。

用法：
  python kimigatame_text.py <scenario_dir> <out.txt> [--patch-root DIR]
"""
import os, re, glob, argparse

PROTAG = '桂華'
EXCLUDE = {'macro.ks', 'start.ks', 'parsermacro.ks', 'gototitle.ks', 'test_manpu.ks'}


def read_ks(p):
    b = open(p, 'rb').read()
    if b[:2] == b'\xff\xfe':
        return b.decode('utf-16')
    if b[:3] == b'\xef\xbb\xbf':
        return b.decode('utf-8-sig')
    if b.count(0) > len(b) * 0.25:
        return b.decode('utf-16-le', 'replace')
    return b.decode('cp932', 'replace')


def split_tags(s):
    out, i, n, buf = [], 0, len(s), ''
    while i < n:
        c = s[i]
        if c != '[':
            buf += c; i += 1; continue
        j, depth = i, 0
        while j < n:
            if s[j] == '[':
                depth += 1
            elif s[j] == ']':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if j >= n:
            k = s.find(']', i + 1)
            if k < 0:
                break
            j = k
        if buf:
            out.append(('text', buf)); buf = ''
        inner = s[i + 1:j]
        m = re.match(r'([^\[\]\s=]+)', inner)
        out.append(('tag', m.group(1) if m else '', inner))
        i = j + 1
    if buf:
        out.append(('text', buf))
    return out


def line_text(s):
    """剥标签；名字宏/emb 内联为默认主角名。"""
    out = []
    for tok in split_tags(s):
        if tok[0] == 'text':
            out.append(tok[1])
        elif tok[1] in ('＠桂華', '＠名前切替', 'emb'):
            out.append(PROTAG)
    return ''.join(out)


NAME_HEAD_RE = re.compile(r'^【[^】]*】')


def extract_file(path):
    t = read_ks(path)
    out, cur = [], []
    for raw in t.split('\n'):
        s = raw.strip()
        if not s:
            if cur:
                out.append(''.join(cur)); cur = []
            continue
        if s.startswith(';') or s.startswith('*') or s.startswith('@'):
            continue
        if s.startswith('[seladd'):
            if cur:
                out.append(''.join(cur)); cur = []
            m = re.search(r'text="([^"]*)"', s)
            if m:
                out.append(m.group(1))
            continue
        if s.startswith('[select'):
            if cur:
                out.append(''.join(cur)); cur = []
            continue
        txt = NAME_HEAD_RE.sub('', line_text(s)).strip()
        if not txt:
            if cur:
                out.append(''.join(cur)); cur = []
            continue
        if not any(ord(c) > 127 for c in txt):
            if cur:
                out.append(''.join(cur)); cur = []
            continue
        cur.append(txt)
    if cur:
        out.append(''.join(cur))
    return out


def cross_box_dual(lines):
    """跨框断引号（一次点击多框）：前框开「/『/（ 未收、紧邻后框正好收 ⇒ 段行+合并行。"""
    def qdel(t):
        return (t.count('「') - t.count('」'), t.count('『') - t.count('』'),
                t.count('（') - t.count('）'))
    out, i, ngrp = [], 0, 0
    while i < len(lines):
        a = lines[i]
        if i + 1 < len(lines):
            b = lines[i + 1]
            da, db = qdel(a), qdel(b)
            for k in range(3):
                if (da[k] > 0 and db[k] < 0 and da[k] + db[k] == 0
                        and da[0] + db[0] == 0 and da[1] + db[1] == 0 and da[2] + db[2] == 0):
                    out.extend([a, b, a + b]); ngrp += 1
                    i += 2
                    break
            else:
                out.append(a); i += 1
            continue
        out.append(a); i += 1
    return out, ngrp


def main():
    ap = argparse.ArgumentParser(description='[PC-JP]君がため、恋し乱れし月の華。 KiriKiri RAT text extractor')
    ap.add_argument('scenario', help='解包后的 xp3data/scenario 目录')
    ap.add_argument('out', help='输出 txt（UTF-8 BOM / LF）')
    ap.add_argument('--patch-root', default='', help='patch2.xp3 解到根目录（同名 .ks 覆盖本体）')
    args = ap.parse_args()

    files = []
    for f in sorted(glob.glob(os.path.join(args.scenario, '*.ks'))):
        b = os.path.basename(f)
        if b in EXCLUDE:
            continue
        if args.patch_root:
            p = os.path.join(args.patch_root, b)
            if os.path.isfile(p):
                f = p
        files.append(f)

    all_lines, ngrp = [], 0
    for f in files:
        ls = extract_file(f)
        ls, g = cross_box_dual(ls)
        ngrp += g
        all_lines.extend(ls)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, 'w', encoding='utf-8-sig', newline='\n') as fh:
        for l in all_lines:
            fh.write(l + '\n')
    print('files=%d lines=%d dual_groups=%d -> %s' % (len(files), len(all_lines), ngrp, os.path.abspath(args.out)))


if __name__ == '__main__':
    main()
