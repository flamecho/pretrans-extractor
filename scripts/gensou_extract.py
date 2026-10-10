#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""蝶の毒 華の鎖 ～幻想夜話～ 全テキスト抽出（KAG3 スクリプト → 表示テキスト）

本体(初回版)と同じ KAG3 記法。scenario/*.txt がシナリオ本体。
仕様は scripts/chou_extract.py と同一（skill §0 準拠）:
  1クリック=1行 / 同一メッセージ内改行は連結 / ルビは親文字のみ /
  [名前置換]→百合子 [名字置換]→野宮 [愛称置換]→ユリ / 【X/Y】→【Y】 /
  名前札【名】行は破棄 / @if は既定名ルート(f.sys_name==0)の真分岐のみ採用 /
  選択肢タグ(seladd 等 text=)は1行1件で出現順に収録。
"""
import os, re, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xp3 import XP3
import gensou_decode as GD
import chou_decrypt as CD

ARC = os.path.join(VNTRANS_HOME, '_work_gensou/_iso/poisonchain_fd/data.xp3')
OUTDIR = os.path.join(VNTRANS_HOME, '提取结果')
OUT = os.path.join(OUTDIR, '蝶の毒 華の鎖 ～幻想夜話～_全文本.txt')
NAME, FAMILY, NICK = '百合子', '野宮', 'ユリ'

TAG = re.compile(r'\[([^\]\n]*)\]')
NAME_TAG = re.compile(r"\[([^\]\n'’=\"=\s]{1,12})['’]([^\]\n]{1,24})\]")
TEXTTAG = re.compile(
    r'\[(seladd|_link|_click|_extmenu|_homepage|_sptool|_readme|_exec|_home)\b'
    r'[^\]]*?\btext\s*=\s*(?:"([^"]*)"|([^\s\]]+))')

PLACEHOLDER = '〓'


def strip_tags(line):
    line = NAME_TAG.sub(lambda m: m.group(1), line)
    line = line.replace('[名前置換]', NAME).replace('[名字置換]', FAMILY).replace('[愛称置換]', NICK)
    line = TAG.sub('', line)
    line = re.sub(r'【([^】/]*)/([^】/]*)】', lambda m: '【%s】' % m.group(2), line)
    return line


def sanitize(s):
    return s.replace('\ufffd', PLACEHOLDER)


def is_text_line(s):
    return bool(strip_tags(s).strip())


def parse_script(text):
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    out, cur, active, stack = [], [], True, []

    def flush():
        nonlocal cur
        if cur:
            s = ''.join(c.strip() for c in cur).strip()
            if s:
                out.append(sanitize(s))
            cur = []

    for ln in lines:
        s = ln.strip()
        if s == '':
            flush(); continue
        if s.startswith(';'):
            continue
        if s.startswith('*'):
            flush(); continue
        if s.startswith('@'):
            core = s[1:].strip(); low = core.lower()
            if low.startswith('if'):
                stack.append(active); flush()
            elif low.startswith('elseif') or low.startswith('else'):
                active = False
            elif low.startswith('endif'):
                if stack:
                    active = stack.pop()
            continue
        if re.fullmatch(r'[!！]?【[^】]*】', strip_tags(s).strip()):
            flush(); continue
        texts = [m.group(2) if m.group(2) is not None else m.group(3)
                 for m in TEXTTAG.finditer(s)]
        texts = [t for t in texts if t and not t.startswith(('%', '&'))]
        if texts:
            flush()
            if active:
                for t in texts:
                    out.append(sanitize(strip_tags(t).strip()))
            continue
        if is_text_line(s):
            if active:
                cur.append(strip_tags(ln))
    flush()
    return out


def natkey(s):
    return [int(x) if x.isdigit() else x for x in re.split(r'(\d+)', s)]


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    x = XP3(ARC)
    cm, bg = GD.build_models(x)
    # シナリオ本体＝scenario/*.txt（endroll/start/macro は表示文なし）
    names = sorted([n for n in x.files
                    if n.startswith('scenario/') and n.lower().endswith('.txt')],
                   key=lambda p: natkey(p.split('/')[-1]))
    total = 0
    per = []
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        for n in names:
            dec, _ = GD.decode(x.read(n), cm, bg, n)
            msgs = parse_script(dec.decode('cp932', 'replace'))
            per.append((n.split('/')[-1], len(msgs)))
            for m in msgs:
                f.write(m + '\n'); total += 1
    print('files=%d  lines=%d' % (len(names), total))
    for k, v in per:
        print('  %-24s %d' % (k, v))
    print(OUT)


if __name__ == '__main__':
    main()
