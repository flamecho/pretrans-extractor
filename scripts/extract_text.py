#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PSP アラビアンズ・シリーズ 脚本テキスト抽出
- 各ゲームの CPK 内 .ks (KiriKiri/KAG) を TOC 順にストリーミング展開
- 1 [message] ブロック = 1 行 (クリック1回分の表示テキスト)
- [br] は同一セリフ内の改行なので結合
- 制御タグ / コメント / ルビ(振り仮名) を除去し、可視テキストのみ出力
- 話者名プレフィックスは付けない (要求通り削除)。本文(「セリフ」等)のみ出力
- 可自定义主角名の占位符を既定名で埋める:
    ロスト  -> [firstname]             -> アイリーン
    ダウト  -> [print value="firstname"] -> アイリーン
  (姓 オラサバル はスクリプト内の固定文本のためそのまま維持)
- [select word="..."] は選択肢テキストとして1行出力
- 出力: UTF-8 (BOM付) 、1ゲーム1ファイル
"""
import os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cpk import CPK

BASE = os.environ.get('VNTRANS_HOME', os.getcwd())

# ロスト nam_*.png -> 日本語話者名 (26名)
# 全て文脈またはダウト側の明示日本語名・クロス対話で検証済
#  (例: nam_idit が nam_eugine を「ユージーン」と呼び、nam_eugine が nam_idit を
#   「イディット」と呼ぶため両者確定)
LOST_NAME_MAP = {
    'nam_roberto.png': 'ロベルト', 'nam_curtis.png': 'カーティス',
    'nam_stuart.png': 'スチュアート', 'nam_tyrone.png': 'タイロン',
    'nam_lille.png': 'ライル', 'nam_shark.png': 'シャーク',
    'nam_meissen.png': 'マイセン', 'nam_michael.png': 'ミハエル',
    'nam_queen.png': '王妃', 'nam_almeida.png': 'アルメダ',
    'nam_cejka.png': 'チェイカ', 'nam_man.png': '男',
    'nam_yuu.png': 'ユウ', 'nam_maze.png': 'メイズ',
    'nam_king.png': '王', 'nam_joshua.png': 'ヨシュア',
    'nam_woman.png': '女', 'nam_totem.png': 'トータム',
    'nam_eugine.png': 'ユージーン', 'nam_dealer.png': 'ディーラー',
    'nam_idit.png': 'イディット', 'nam_hatena.png': '？',
    'nam_buka.png': '部下', 'nam_roley.png': 'ローレイ',
    'nam_bartender.png': 'バーテンダー', 'nam_aric.png': 'アリク',
}

# 可自定义主角名的既定値 (ユーザー提供: アイリーン＝オラサバル / 名=アイリーン)
HEROINE_DEFAULT = 'アイリーン'


def decode(raw):
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        return raw.decode('cp932')


def clean_inner(s):
    # 行内改行タグ -> 結合 (同一テキストボックス内)
    s = re.sub(r'\[br\s*/?\]', '', s, flags=re.I)
    # ルビ: 本体(text=)のみ保持、読み(ruby=/[rt])は除去
    s = re.sub(r'\[ruby\b[^\]]*?text="([^"]*)"[^\]]*\]', r'\1', s, flags=re.I)
    s = re.sub(r'\[ruby\b[^\]]*\]', '', s, flags=re.I)
    s = re.sub(r'\[rb\b[^\]]*\](.*?)\[/rb\]', r'\1', s, flags=re.I | re.S)
    s = re.sub(r'\[rt\b[^\]]*\].*?\[/rt\]', '', s, flags=re.I | re.S)
    # 残余の制御タグ ([wait]/[cm]/[font]/[color] 等) を除去
    s = re.sub(r'\[[^\]\[]+\]', '', s)
    # ソース上の改行・タブを除去
    s = s.replace('\r', '').replace('\n', '').replace('\t', '')
    return s.strip()


def fill_heroine(body, game):
    """可自定义主角名の占位符を既定名(アイリーン)で埋める。"""
    if game == 'lost':
        return body.replace('[firstname]', HEROINE_DEFAULT)
    # ダウト: [print value="firstname"] (他の [print ...] は clean_inner で除去)
    return re.sub(r'\[print\b[^\]]*?value=["\']firstname["\'][^\]]*\]',
                  HEROINE_DEFAULT, body, flags=re.I)


def speaker_of(attrs, game):
    w = re.search(r'window="([^"]*)"', attrs)
    nm = re.search(r'name="([^"]*)"', attrs)
    wv = w.group(1) if w else ''
    nmv = nm.group(1) if nm else ''
    if game == 'lost':
        return LOST_NAME_MAP.get(nmv)          # kya のみ nam_ を持つ
    else:  # doubt: kyara ウィンドウの name はそのまま日本語
        if wv == 'kyara' and nmv:
            return nmv
        return None
    # 注: 現行仕様では話者名プレフィックスを出力しない (extract_text 側で未使用)


MSG_RE = re.compile(r'\[message\b[^\]]*\].*?\[/message\]', re.S | re.I)
SEL_RE = re.compile(r'\[select\b[^\]]*\]', re.I)


def parse_ks(text, game):
    lines = []
    toks = []
    for m in MSG_RE.finditer(text):
        toks.append(('msg', m.start(), m.group(0)))
    for m in SEL_RE.finditer(text):
        toks.append(('sel', m.start(), m.group(0)))
    toks.sort(key=lambda x: x[1])
    for kind, _, tok in toks:
        if kind == 'msg':
            am = re.match(r'\[message\b([^\]]*)\]', tok, flags=re.I)
            attrs = am.group(1) if am else ''
            body = tok.split(']', 1)[1].rsplit('[/message]', 1)[0]
            body = fill_heroine(body, game)
            inner = clean_inner(body)
            if not inner:
                continue
            # 話者名プレフィックスは付けない (本文のみ)
            lines.append(inner)
        else:
            wm = re.search(r'word="([^"]*)"', tok)
            if wm:
                opt = clean_inner(wm.group(1))
                if opt:
                    lines.append(opt)
    return lines


def extract_game(cpk_paths, game, out_path):
    all_lines = []
    seen = set()
    for cpk_path in cpk_paths:
        if not os.path.exists(cpk_path):
            print('  [skip] not found:', cpk_path)
            continue
        print('  opening', cpk_path)
        cpk = CPK(cpk_path)
        for e in cpk.entries:
            name = e.get('name') or ''
            if not name.lower().endswith('.ks'):
                continue
            if name in seen:
                continue
            seen.add(name)
            data = cpk.raw(e)
            text = decode(data)
            all_lines.extend(parse_ks(text, game))
    with open(out_path, 'w', encoding='utf-8-sig') as o:
        o.write('\n'.join(all_lines))
        o.write('\n')
    return len(all_lines)


if __name__ == '__main__':
    lost = extract_game(
        [os.path.join(BASE, 'iso', 'lost', 'data.cpk')], 'lost',
        os.path.join(BASE, 'アラビアンズ・ロスト.txt'))
    print('ロスト  出力行数:', lost)

    doubt = extract_game(
        [os.path.join(BASE, 'iso', 'doubt', 'DATA0.cpk'),
         os.path.join(BASE, 'iso', 'doubt', 'DATA1.cpk')], 'doubt',
        os.path.join(BASE, 'アラビアンズ・ダウト.txt'))
    print('ダウト  出力行数:', doubt)
