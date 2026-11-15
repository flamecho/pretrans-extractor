#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[JP]Voice -Be Quite in the Dark-（TVP/KiriKiri 2.24 ＋ KAG3）全文本提取。

容器：外置 `data.xp3`（4,359,871 B，191 成员）＋ `voice_bqitdver.01.eXe` ＋ `wuvorbis.dll`。
正文：`scenario/first.ks`（本篇＋4 结局）与 `scenario/av_ex.ks`（アナザー＝EXTR）。
系统不收：el.ks（エンディングリスト）/ autoInsertLabel(.ks/_test)/ changeColorLink / rclick_tjs21。

L0（`first.ks` 宏）：
  `[plc]` = `@p @label @cm` ⇒ 清屏＋点击 ＝ **框结束**（一次点击一行）
  `[l]` = 行クリック待ち（不 clear）⇒ **同框再一次点击（段）**
  `[p]` / `[cm]` / `[er]` / `[ct]` ⇒ 框结束；`[r]`＝改行合并
  `[nowait]【名】[endnowait]`：名札写在 message0 正文框内 ⇒ 与台词同行保留（`--inline-name`）
  `[ruby text=読み]基底`：留基底字，读音不入正文

双版：同一框内 `[l]` ≥2 ⇒ 段行＋合并行（同框各段拼接）；跨框断引号不合并。

用法: python voice_bq_text.py <scenario_dir> <out.txt>
"""
import sys, os, re, argparse

FILES = ['first.ks', 'av_ex.ks']


def read_ks(p):
    b = open(p, 'rb').read()
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
            if s[j] == '[': depth += 1
            elif s[j] == ']':
                depth -= 1
                if depth == 0: break
            j += 1
        if j >= n:
            k = s.find(']', i + 1)
            if k < 0: break
            j = k
        if buf:
            out.append(('text', buf)); buf = ''
        inner = s[i+1:j]
        m = re.match(r'([a-zA-Z0-9_]+)', inner)
        out.append(('tag', m.group(1) if m else '', inner))
        i = j + 1
    if buf: out.append(('text', buf))
    return out


def extract(path, stats):
    t = read_ks(path).replace('\r\n', '\n').replace('\r', '\n')
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
            events.append(('box', list(segs)))
            stats['boxes'] += 1
            if len(segs) > 1:
                stats['dual_boxes'] += 1
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
            if name in ('plc', 'p', 'cm', 'er', 'ct', 'endtxt'):
                close_box()
            elif name == 'l':
                close_seg()
            # nowait/endnowait/ruby/title/button/... 无文本、不断框
    close_box()

    lines = []
    for ev in events:
        box = ev[1]
        if len(box) == 1:
            lines.append(box[0])
            stats['seg_chars'] += len(box[0])
        else:
            lines.extend(box)
            lines.append(''.join(box))
            stats['seg_chars'] += sum(len(x) for x in box)
            stats['merged_chars'] += len(''.join(box))
    return lines


def main():
    ap = argparse.ArgumentParser(description='[JP]Voice -Be Quite in the Dark- KAG3 extractor')
    ap.add_argument('scenario')
    ap.add_argument('out')
    a = ap.parse_args()
    stats = dict(boxes=0, dual_boxes=0, lines=0, files=0, seg_chars=0, merged_chars=0)
    out = []
    for fn in FILES:
        p = os.path.join(a.scenario, fn)
        if not os.path.isfile(p):
            continue
        stats['files'] += 1
        out.extend(extract(p, stats))
    stats['lines'] = len(out)
    with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        for l in out:
            f.write(l + '\n')
    print('files=%d boxes=%d dual_boxes=%d lines=%d seg_chars=%d merged_chars=%d'
          % (stats['files'], stats['boxes'], stats['dual_boxes'], stats['lines'],
             stats['seg_chars'], stats['merged_chars']))
    print('-> ' + a.out)


if __name__ == '__main__':
    main()
