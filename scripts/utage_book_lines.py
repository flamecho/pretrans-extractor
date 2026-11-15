#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ワンド オブ フォーチュン Ｒ２ ～時空に沈む黙示録～（Switch / Unity + Utage）剧本提取

数据链：NSP → Program NCA(CTR) → RomFS → `Data/StreamingAssets/WandsOfFortune/Switch/
wandsoffortune.scenarios.asset`（UnityFS，29 个 Utage `.book` MonoBehaviour）

切行判据（L0）：Utage 一条 Text 命令 = 一个 AdvPage = 一次点击；单元格内 `\\n`（含紧随的全角
缩进）是框内排版换行 ⇒ 合并进同一行。
说话人：名字在 **独立列 Arg1（独立名字窗）** ⇒ 整列丢弃，不并入正文。
主角名：`<param==Name>` → 官方默认名「ルル」。

用法：python wfr2_text.py <scenarios.asset> --out <txt> [--json <dump.json>]
"""
import argparse
import json
import re
import struct
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))
import UnityPy
from dd_utage import parse_book

TEXT_CMDS = ('', 'Text', 'TextMultiVoice', 'TextVoiceIfDefaultName')
SEL_CMD = 'Selection'
DEFAULT_NAME = 'ルル'
SKIP_BOOKS = {'test.book', 'Test.book', 'TestKojima.book'}   # 开发用测试书（大小写两版都见过）
TAG_PAT = re.compile(r'</?(?:ruby|tips|color|size|speed)[^>]*>')
PARAM_PAT = re.compile(r'<param==([^>]*)>')


def variants(t):
    """按「换行 + 行首「」」切开一格内的多个变体；其余换行是框内排版换行。"""
    t = t.replace('\r\n', '\n').replace('\r', '\n').replace('\\n', '\n')
    out = []
    for p in re.split(r'\n(?=「)', t):
        p = re.sub(r'\n[\u3000 ]*', '', p).strip('\u3000 \t')
        if p:
            out.append(p)
    return out


def clean(t):
    vs = variants(t)
    if not vs:
        return ''
    # ★ 同一页里并存「字面名版」与「<param==Name> 宏版」时只留第一版（替换后同文）——
    #   本作仅 2 格有此形态（1100-1107:1102 row646/648），不这样处理会把同一句输出两次。
    head = vs[0].replace('<param==Name>', DEFAULT_NAME)
    keep = [vs[0]]
    for v in vs[1:]:
        if v.replace('<param==Name>', DEFAULT_NAME) == head:
            continue
        keep.append(v)
    t = ''.join(keep)
    t = PARAM_PAT.sub(DEFAULT_NAME, t)
    t = TAG_PAT.sub('', t)
    return t.strip('\u3000 \t')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('--out')
    ap.add_argument('--json')
    a = ap.parse_args()

    env = UnityPy.load(a.src)
    books, order = {}, None
    for o in env.objects:
        if o.type.name != 'MonoBehaviour':
            continue
        try:
            tt = o.read_typetree()
        except Exception:
            tt = {}
        if 'dataList' in tt and order is None:
            order = [p['m_PathID'] for p in tt['dataList']]
        d = o.get_raw_data()
        try:
            b = parse_book(d)
        except Exception:
            continue
        if b['name'].endswith('.book') and b['end'] == len(d):
            b['path_id'] = o.path_id
            books[b['path_id']] = b

    by_id = books
    seq = [by_id[i] for i in order if i in by_id] if order else sorted(books.values(), key=lambda b: b['name'])
    print('[i] books=%d 章节表=%s' % (len(books), 'yes' if order else 'no'))

    lines, stat, skipped = [], {}, []
    for b in seq:
        nm = b['name']
        if nm in SKIP_BOOKS:
            skipped.append(nm)
            continue
        cnt = 0
        for sh in b['sheets']:
            rows, hrow = sh['rows'], sh['header_row']
            if not rows or hrow >= len(rows):
                continue
            cols = {c.strip(): i for i, c in enumerate(rows[hrow]['cells'])}
            ti = cols.get('Text')
            if ti is None:
                continue
            for r in rows:
                if r is rows[hrow] or r['comment']:
                    continue
                c = r['cells']
                if not c or c[0].startswith('*'):
                    continue
                if c[0] not in TEXT_CMDS and c[0] != SEL_CMD:
                    continue
                if ti >= len(c):
                    continue
                t = clean(c[ti])
                if not t:
                    continue
                lines.append(t)
                cnt += 1
        stat[nm] = cnt

    print('[i] 跳过测试书: %s' % (skipped,))
    print('[i] 行数=%d  有正文的书=%d' % (len(lines), sum(1 for v in stat.values() if v)))
    if a.json:
        json.dump({'order': [b['name'] for b in seq], 'stat': stat,
                   'skipped': skipped, 'lines': lines},
                  open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if a.out:
        with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write('\n'.join(lines) + '\n')
        print('[i] -> %s' % a.out)


if __name__ == '__main__':
    main()
