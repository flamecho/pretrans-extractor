#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""蝶の毒 華の鎖 全テキスト抽出（KAG3 スクリプト → 表示テキスト）

仕様:
  - 1クリック = 1行（メッセージ）。空行／ラベル／@if で区切る。
  - 同一メッセージ内の行は連結（改行を除去）。
  - [漢字'よみ] → 漢字 / [名前置換]→百合子 / [名字置換]→野宮 / [愛称置換]→ユリ
  - 【X/Y】→【Y】(未開示表記。作者注記 ;■#表記 準拠)
  - 名前札【名前】行は出力しない（skill §0「不加说话人前缀」準拠。名前札は独立行で
    直後の台詞と別物なので、メッセージの区切りとして扱い捨てる）
  - @if/@else: 既定名ルート(f.sys_name==0)の分岐のみ採用。
"""
import os, re, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SCEN = os.path.join(VNTRANS_HOME, '_work_chou/ks')
OUTDIR = os.path.join(VNTRANS_HOME, '提取结果')
NAME, FAMILY, NICK = '百合子', '野宮', 'ユリ'

TAG = re.compile(r'\[([^\]\n]*)\]')
# ルビは「基底語」に = " ' を含まない場合のみ（[seladd ... cond='...'] を誤ってルビ扱いしない）
NAME_TAG = re.compile(r"\[([^\]\n'’=\"=\s]{1,12})['’]([^\]\n]{1,24})\]")
# 上屏文字を持つタグ（text= が実表示文字列。%xx / &xx は未解決参照なので除外）
TEXTTAG = re.compile(
    r'\[(seladd|_link|_click|_extmenu|_homepage|_sptool|_readme|_exec|_home|_sptool)\b'
    r'[^\]]*?\btext\s*=\s*(?:"([^"]*)"|([^\s\]]+))')

def strip_tags(line):
    # ruby [漢字'よみ] → 漢字
    line = NAME_TAG.sub(lambda m: m.group(1), line)
    # 名前マクロ
    line = line.replace('[名前置換]', NAME).replace('[名字置換]', FAMILY).replace('[愛称置換]', NICK)
    # 残りのタグ除去
    line = TAG.sub('', line)
    # 【X/Y】→【Y】
    line = re.sub(r'【([^】/]*)/([^】/]*)】', lambda m: '【%s】' % m.group(2), line)
    return line


PLACEHOLDER = '〓'


def sanitize(s):
    return s.replace('\ufffd', PLACEHOLDER)

def is_text_line(s):
    """タグ・コメントを除いて可視文字が残るか"""
    t = strip_tags(s)
    return bool(t.strip())

def parse_script(text):
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    out = []
    cur = []
    active = True
    stack = []
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
            # TJS 行（@if/@else/@endif は分岐制御、他は無視）
            core = s[1:].strip()
            low = core.lower()
            if low.startswith('if'):
                stack.append(active)          # 真分岐を採用
                flush()
            elif low.startswith('elseif'):
                active = False                # 条件分岐の else 側はスキップ
            elif low.startswith('else'):
                active = False
            elif low.startswith('endif'):
                if stack: active = stack.pop()
            continue
        # 名前札（話者ラベル）は出力しない。直前メッセージを閉じるだけ。
        # 原作に 1 箇所だけ「!【警官２】」という筆記ゆれ（兄弟行は【警官１】）があるため ! を許容。
        if re.fullmatch(r'[!！]?【[^】]*】', strip_tags(s).strip()):
            flush(); continue
        # 選択肢 / リンク等の「上屏文字」タグは、その文字列自体を 1 行として出力
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

def collect(tag):
    res = []
    for fn in sorted(os.listdir(SCEN)):
        if not fn.startswith(tag + '__'): continue
        sub = fn[len(tag) + 2:]
        text = open(os.path.join(SCEN, fn), encoding='utf-8').read()
        msgs = parse_script(text)
        res.append((sub, msgs))
    res.sort(key=lambda kv: natkey(kv[0]))
    return res

def write(entries, path, header=None):
    tot = 0
    with open(path, 'w', encoding='utf-8-sig', newline='\n') as f:
        if header:
            f.write(header)
        for i, (sub, msgs) in enumerate(entries):
            f.write('%s\n' % msgs and '' or '')
            for m in msgs:
                f.write(m + '\n')
                tot += 1
    return tot

def main():
    os.makedirs(OUTDIR, exist_ok=True)
    # システム / UI テキストは出力しない（skill §0：交付物は剧本正文＋选项のみ）
    scen = [(s, m) for s, m in collect('main')
            if s.startswith('scenario__')]
    toku = [(s, m) for s, m in collect('toku')
            if s.startswith('scenario__')]
    scen.sort(key=lambda kv: natkey(kv[0]))
    toku.sort(key=lambda kv: natkey(kv[0]))

    p1 = os.path.join(OUTDIR, '蝶の毒 華の鎖_全文本.txt')
    with open(p1, 'w', encoding='utf-8-sig', newline='\n') as f:
        n1 = 0
        for sub, msgs in scen:
            for m in msgs:
                f.write(m + '\n'); n1 += 1
    p3 = os.path.join(OUTDIR, '蝶の毒 華の鎖 初回特典_全文本.txt')
    with open(p3, 'w', encoding='utf-8-sig', newline='\n') as f:
        n3 = 0
        for sub, msgs in toku:
            for m in msgs:
                f.write(m + '\n'); n3 += 1
    print('本体シナリオ files=%d lines=%d' % (len(scen), n1))
    print('初回特典   files=%d lines=%d' % (len(toku), n3))
    print(p1); print(p3)

if __name__ == '__main__':
    main()
