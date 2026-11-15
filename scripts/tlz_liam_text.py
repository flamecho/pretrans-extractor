#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Takuyo「LIAM」引擎（Fragrance Tale PC 2001）→ 一台本一台词框的正文。

容器：`DATA/srptdata.tlz` = **TLZ1**（见 `scripts/tlz.py`），成员 451 个：`.s` / `.dat` / `.odi`。

脚本编码（L0，字节层，本作实测）
  · 标签字节 **`0x40`** ＝ 命令前缀，后跟 1 字节子码；其余字节是 **cp932 字符（2 字节）** 或 `0x0A`（框内换行）。
  · `40 09 <u8>` … `40 08` ＝ **一段正文**：`0x0A` 分行的 1〜4 行，**每行补足 20 个全角字**
    （实测行宽峰值 20；末行常不补）。⇒ 一屏一次点击（同为 1:1：`40 09` 8,152 ／ 语音 `40 0A vNNNN` 7,919）。
  · `40 15 <u32 x> <u32 y> <0 结尾字符串>` ＝ **选项**（画面坐标 + 标签），本作 44 条 —— 是「谁に会いに行く/何と言う」的选择。
  · `40 41`（＋后随 1〜3 个全角空格）＝ **主角名スロット**，本作即「リアム」
    （官方 story 页原文「主人公リアム」；精灵名 `liam_NN`；地名表「05：リアムの部屋」）。
  · 其余子码：`40 00`/`40 01 <名字>`/`40 02 <名字>`/`40 04`＝立绘，`40 0A vNNNN`＝语音，`40 10 mNN`＝BGM，
    `40 13 seNN`＝SE，`40 05`/`40 06`/`40 0D`/`40 0F`/`40 11`/`40 12`/`40 16`＝演出 —— 均不含正文。

用法
  python scripts/tlz_liam_text.py <解出的 srptdata 目录> <out.txt> [--name リアム] [--order 顺序文件]
"""
import argparse
import glob
import os
import re
import struct
import sys

TAG = 0x40
TEXT_START = 0x09
TEXT_END = 0x08
OPTION = 0x15
NAME_SLOT = 0x41
LEAD = re.compile(rb'[\x81-\x9f\xe0-\xfc]')


def is_lead(b):
    return 0x81 <= b <= 0x9f or 0xe0 <= b <= 0xfc


def is_trail(b):
    return 0x40 <= b <= 0x7e or 0x80 <= b <= 0xfc


def segments(ln):
    """把一个框内的行按「独白段界」切成若干段（纯结构判据，与内容无关）。

    段界：第 k 行（k>0）满足以下任一
      (A) 该行以全角「（」开头        —— 独白开括弧换行起
      (B) 上一行以「（」开头且以「）」收尾 —— 整行独白结束、下一行换回台词
    单段页不切。
    """
    segs, cur = [], []
    for k, s in enumerate(ln):
        if k > 0:
            prev = ln[k - 1]
            if s.startswith('（') or (prev.startswith('（') and prev.endswith('）')):
                segs.append(''.join(cur)); cur = []
        cur.append(s)
    if cur:
        segs.append(''.join(cur))
    return segs


def parse(path, name='リアム', dual=False):
    """→ [(kind, text)]；kind ∈ {'text','option'}。dual=True 时多段框先列段行再列合并行。"""
    d = open(path, 'rb').read()
    out = []
    i = 0
    n = len(d)
    while i < n - 1:
        if d[i] != TAG:
            i += 1
            continue
        sub = d[i + 1]
        if sub == TEXT_START:
            j = i + 3
            lines, cur = [], []
            closed = False
            while j < n:
                b = d[j]
                if b == 0x0a:
                    lines.append(''.join(cur)); cur = []; j += 1; continue
                if b == TAG:
                    if j + 1 < n and d[j + 1] == NAME_SLOT:
                        cur.append(name); j += 2
                        while j + 1 < n and d[j] == 0x81 and d[j + 1] == 0x40:
                            j += 2          # 名札槽的定宽补白
                        continue
                    closed = True           # 任何非名札槽的命令字节都收束本段
                    break
                if is_lead(b) and j + 1 < n and is_trail(d[j + 1]):
                    cur.append(d[j:j + 2].decode('cp932', 'replace')); j += 2; continue
                if 0xa1 <= b <= 0xdf or 0x20 <= b <= 0x7e:      # 半角片假名 / ASCII（作者偶尔手打）
                    cur.append(bytes([b]).decode('cp932', 'replace')); j += 1; continue
                break
            if cur:
                lines.append(''.join(cur))
            ln = [x.rstrip('\u3000') for x in lines]
            body = ''.join(ln)
            if closed and body.strip('\u3000 '):
                if dual:
                    segs = segments(ln)
                    assert ''.join(segs) == body, (path, segs, body)
                    if len(segs) > 1:
                        for sg in segs:
                            out.append(('text', sg))
                        out.append(('text', body))
                    else:
                        out.append(('text', body))
                else:
                    out.append(('text', body))
            i = j
        elif sub == OPTION:
            if i + 10 <= n:
                p = i + 10
                buf = []
                while p < n and d[p] != 0:
                    b = d[p]
                    if is_lead(b) and p + 1 < n and is_trail(d[p + 1]):
                        buf.append(d[p:p + 2].decode('cp932', 'replace')); p += 2
                    elif 32 <= b < 127:
                        buf.append(chr(b)); p += 1
                    else:
                        break
                s = ''.join(buf).strip('\u3000 ')
                if s:
                    out.append(('option', s))
            i += 2
        else:
            i += 2
    return out


GROUPS = [
    ('opening', [r'^op-1xx\.dat$', r'^op-2\.dat$', r'^op-2\.s$']),
    ('daily', [r'^asa\.', r'^school\.', r'^koudou\.', r'^seisui\.', r'^mori[a-d]\.', r'^schget\.', r'^yoru\.']),
    ('routes', [r'^[1-8](koku|leve|nev|neve|yeve)']),
    ('ned', [r'^ned']),
    ('odai', [r'^odai-.*\.odi$']),
    ('ev', [r'^cp-', r'^ate\d', r'^jama\d']),
    ('homon', [r'^homon']),
    ('hint', [r'^hint[12]\.']),
    ('variant', [r'^[pr]-']),
]


def ordered(dirpath, explicit=None):
    files = sorted(os.path.basename(f) for f in glob.glob(os.path.join(dirpath, '*'))
                   if os.path.isfile(f))
    files = [f for f in files if f.lower().endswith(('.s', '.dat', '.odi'))]
    if explicit:
        want = [l.strip() for l in open(explicit, encoding='utf-8') if l.strip()]
        return [f for f in want if f in files] + [f for f in files if f not in want]
    picked, used = [], set()
    for _tag, pats in GROUPS:
        for pat in pats:
            rx = re.compile(pat)
            for f in files:
                if f not in used and rx.match(f):
                    picked.append(f); used.add(f)
    picked += [f for f in files if f not in used]
    return picked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dir')
    ap.add_argument('out')
    ap.add_argument('--name', default='リアム')
    ap.add_argument('--order')
    ap.add_argument('--stat', action='store_true')
    ap.add_argument('--dual', action='store_true',
                    help='双版：独白段界（行首「（」／整行独白收尾）处切段，先列段行再列合并行')
    a = ap.parse_args()
    lines, st = [], {'text': 0, 'option': 0, 'file': 0, 'empty': 0}
    for f in ordered(a.dir, a.order):
        seg = parse(os.path.join(a.dir, f), a.name, dual=a.dual)
        if not seg:
            st['empty'] += 1
            continue
        st['file'] += 1
        for kind, s in seg:
            lines.append(s)
            st[kind] += 1
    with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('文件 %d（空 %d）／正文 %d 行 ＋ 选项 %d 行 ＝ %d 行 / %d 字'
          % (st['file'], st['empty'], st['text'], st['option'], len(lines),
             sum(len(x) for x in lines)))


if __name__ == '__main__':
    main()
