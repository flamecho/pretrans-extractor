#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《逢魔が刻 ～かくりよの縁～》系统/资料文本整理

用語辞典 = FlagDatabase.dat (見出し語 + 読み) ＋ FOAFDatabase.dat (解説文)
  · FlagDatabase 记录 {u32 id, u32 5700+id, u32 5850+id, u32 見出し語off, u32 読みoff, u32, u32}
  · FOAFDatabase 记录 {u32 id, u32 a(=FlagDatabase の id), u32 b(行番号), u32 テキストoff}
  两者 id/a 均 1..131，一一对应 → 一条 = 【見出し語】解説（读音不输出）。

输出格式（用户既定规范）：UTF-8-BOM / 纯 LF / 一条一行 / 行内换行合并。
"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nsac import Nsac  # noqa

JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff\uff00-\uffef\u3000-\u303f]')
BIN = re.compile(r'[\x00-\x08\x0e-\x1f\x7f-\x9f]')
DB = os.path.join(VNTRANS_HOME, 'tmp_ouma/dec/database.dat')


def dbread(b):
    return struct.unpack_from('<IIII', b, 0)


def gstr(b, doff, o):
    if doff + o >= len(b):
        return ''
    e = b.find(b'\x00', doff + o)
    return b[doff + o:e].decode('utf-8', 'replace')


def split_strings(b):
    out, seen, pos = [], set(), 0
    while pos < len(b):
        e = b.find(b'\x00', pos)
        if e < 0:
            e = len(b)
        s = b[pos:e]
        if s:
            t = s.decode('utf-8', 'replace')
            if t not in seen and not BIN.search(t) and JP.search(t) and len(t) >= 1:
                seen.add(t)
                out.append(t)
        pos = e + 1
    return out


def clean(s):
    return s.replace('\u3000', ' ').replace('\n', '').replace('\r', '')


def build_glossary(raw):
    """返回 ['【見出し語】解説', ...]（131 条）"""
    fb = raw.get('FlagDatabase.dat', b'')
    cnt, rs, doff, hs = dbread(fb)
    terms = {}
    for i in range(cnt):
        v = struct.unpack_from('<%dI' % (rs // 4), fb, hs + i * rs)
        terms[v[0]] = gstr(fb, doff, v[3])
    ob = raw.get('FOAFDatabase.dat', b'')
    cnt2, rs2, doff2, hs2 = dbread(ob)
    expl = {}
    for i in range(cnt2):
        v = struct.unpack_from('<%dI' % (rs2 // 4), ob, hs2 + i * rs2)
        expl.setdefault(v[1], []).append((v[2], gstr(ob, doff2, v[3])))
    out = []
    for tid in sorted(terms):
        body = ''.join(t for _, t in sorted(expl.get(tid, [])))
        out.append('【%s】%s' % (clean(terms[tid]), clean(body)))
    return out


GROUPS = [
    ('キーワード（ライアーズアート）', ['Keyword.dat']),
    ('選択肢（セレクター／セレクト情報）', ['Selecter.dat', 'SelectInfo.dat']),
    ('ゲーム文字列（選択肢ラベル・フラグなど）', ['GameString.dat']),
    ('ヒント', ['HintDatabase.dat']),
    ('エンディング回想', ['Memory.dat', 'ExtraEndingList.dat']),
]


def build_storytext(raw):
    """物語テキスト = ExtraCG（【タイトル】解説）＋ EventCG（CG 名）。
    ExtraCG 记录 {u32 id, a, b, c, u32 タイトルoff, u32 num, u32 解説off×8}
    EventCG 记录 {u32 id, a, b, c, u32 タイトルoff, u32, u32}"""
    out = []
    b = raw.get('ExtraCG.dat', b'')
    cnt, rs, doff, hs = dbread(b)
    for i in range(cnt):
        v = struct.unpack_from('<%dI' % (rs // 4), b, hs + i * rs)
        title = clean(gstr(b, doff, v[4]))
        if not title:
            continue
        desc = clean(''.join(gstr(b, doff, o) for o in v[6:]))
        out.append('【%s】%s' % (title, desc))
    b = raw.get('EventCG.dat', b'')
    cnt, rs, doff, hs = dbread(b)
    for i in range(cnt):
        v = struct.unpack_from('<%dI' % (rs // 4), b, hs + i * rs)
        t = clean(gstr(b, doff, v[4]))
        if t:
            out.append(t)
    seen, res = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            res.append(x)
    return res


def main():
    arc = Nsac(open(DB, 'rb').read())
    raw = {n: arc.b[o:o + s] for n, o, s in arc.named}
    outdir = os.path.join(VNTRANS_HOME, 'tmp_ouma/out')
    os.makedirs(outdir, exist_ok=True)

    glossary = build_glossary(raw)
    lines = ['■ 用語辞典（見出し語＋解説）'] + glossary
    for title, files in GROUPS:
        sec, seen = [], set()
        for fn in files:
            if fn not in raw:
                continue
            for x in split_strings(raw[fn]):
                if x not in seen:
                    seen.add(x)
                    sec.append(x)
        if sec:
            lines.append('')
            lines.append('■ ' + title)
            lines.extend(sec)

    story = build_storytext(raw)
    if story:
        lines.append('')
        lines.append('■ 物語テキスト（CG・イベント解説）')
        lines.extend(story)

    txt = '\n'.join(lines).lstrip('\n') + '\n'
    open(os.path.join(outdir, '逢魔が刻_ゲーム内テキスト.txt'),
         'w', encoding='utf-8-sig', newline='\n').write(txt)
    open(os.path.join(outdir, '逢魔が刻_用語辞典.txt'),
         'w', encoding='utf-8-sig', newline='\n').write('\n'.join(glossary) + '\n')
    print('glossary=%d  total_lines=%d' % (len(glossary), len(lines)))


if __name__ == '__main__':
    main()
