# -*- coding: utf-8 -*-
"""[JP]Voice（TVP/KiriKiri 2.24 ＋ KAG3 ／ `data.xp3`）全文本提取。

源：`[JP]Voice.exe`（RAR5 SFX，密码 otoama/otoame）→ `data.xp3`（258 成员）＋ voice.eXe ＋ wuvorbis.dll ＋ readme.txt。
正文：`scenario/first.ks`（本篇＋7 END 分支）。系统/画廊/结局列表/STAFF/右键菜单脚本不收。

L0（`first.ks` 宏 `plc` = `@p @label @cm`）：
  `[plc]` / `[p]` / `[cm]` / `[er]` / `[ct]` / `[endtxt]` ⇒ 清屏＋点击 ＝ **框结束**
  `[l]` ＝ 行クリック待ち（不清屏）⇒ **同框再一次点击 ＝ 段界**
  `[nowait]【名】[endnowait]` 名札写在 message0 正文框内 ⇒ 与台词同行保留
  `[r]` 改行 ⇒ 同框合并

双版：同一框内 `[l]` ≥2 ⇒ 段行＋合并行（同框拼接，确有同框依据）；跨框断引号不合并。

用法：
    python scripts/voice_extract.py --xp3 "<data.xp3>" --verify
    python scripts/voice_extract.py --xp3 "<data.xp3>" --out "提取结果/[JP]Voice.txt"
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xp3 import XP3

FILES = ['scenario/first.ks']
BOX_END = {'plc', 'p', 'cm', 'er', 'ct', 'endtxt'}


def read_ks(b):
    if b[:3] == b'\xef\xbb\xbf':
        return b.decode('utf-8-sig')
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
        m = re.match(r'([a-zA-Z0-9_]+)', inner)
        out.append(('tag', m.group(1) if m else '', inner))
        i = j + 1
    if buf:
        out.append(('text', buf))
    return out


def extract(text, stats):
    t = text.replace('\r\n', '\n').replace('\r', '\n')
    events = []
    segs, buf = [], ''
    in_script = False

    def close_seg():
        nonlocal buf
        s = buf.strip()
        if s:
            segs.append(s)
        buf = ''

    def close_box():
        nonlocal segs
        close_seg()
        if segs:
            events.append(list(segs))
            stats['boxes'] += 1
            if len(segs) > 1:
                stats['dual_boxes'] += 1
                stats['extra_segs'] += len(segs)
            segs = []

    for raw in t.split('\n'):
        s = raw.strip()
        if in_script:
            if s.startswith('@endscript') or s == '[endscript]':
                in_script = False
            continue
        if s.startswith('@iscript') or s == '[iscript]':
            in_script = True
            continue
        if not s or s[0] in ';*':
            continue
        if s.startswith('@'):
            continue
        for tok in split_tags(s.rstrip('\\')):
            if tok[0] == 'text':
                buf += tok[1]
                continue
            name = tok[1]
            if name in BOX_END:
                close_box()
            elif name == 'l':
                close_seg()
    close_box()
    return events


def main():
    ap = argparse.ArgumentParser(description='[JP]Voice（KAG3）文本提取')
    ap.add_argument('--xp3', required=True)
    ap.add_argument('--out')
    ap.add_argument('--verify', action='store_true')
    a = ap.parse_args()

    x = XP3(a.xp3)
    print('XP3 成员 %d' % len(x.files))
    stats = dict(boxes=0, dual_boxes=0, extra_segs=0, files=0)
    lines, all_boxes = [], []
    for fn in FILES:
        if fn not in x.files:
            print('  ⚠ 缺脚本', fn); continue
        stats['files'] += 1
        boxes = extract(read_ks(x.read(fn)), stats)
        all_boxes.extend(boxes)
        for box in boxes:
            lines.extend(box)
            if len(box) > 1:
                lines.append(''.join(box))
    print('脚本 %(files)d 本／框 %(boxes)d（多段框 %(dual_boxes)d）/ 段数合计 %(extra_segs)d'
          % stats)
    print('成品 %d 行 / %d 字' % (len(lines), sum(len(x) for x in lines)))

    # 跨框断引号（只报告，不合并）
    groups = []
    i = 0
    while i < len(lines) - 1:
        if lines[i].count('「') - lines[i].count('」') > 0:
            for j in range(i + 1, min(i + 4, len(lines))):
                if lines[j].count('」') - lines[j].count('「') > 0:
                    groups.append((i, j)); i = j; break
        i += 1
    print('跨框断引号 %d 组（不同框，不合并）' % len(groups))
    for i, j in groups:
        print('  #%d %r … #%d %r' % (i + 1, lines[i][:34], j + 1, lines[j][-34:]))
    unbal = sum(1 for l in lines if l.count('「') != l.count('」') or l.count('（') != l.count('）'))
    print('未平衡行 %d（段行半闭属预期；合并行闭合）' % unbal)

    if a.out and not a.verify:
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        with open(a.out, 'wb') as f:
            f.write(b'\xef\xbb\xbf' + ''.join(x + '\n' for x in lines).encode('utf-8'))
        print('写出 %s（%d B）' % (a.out, os.path.getsize(a.out)))


if __name__ == '__main__':
    main()
