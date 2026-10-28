#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""猛獣使いと王子様 ～Flower & Snow～ for Nintendo Switch —— 成品构建。

链路：XCI -> NCA -> RomFS/CONTENTS/GAME_01(Flower)/GAME_02(Snow).cpk -> script/(STCM2L, UTF-8)
成行：见 scripts/kedamono_ns_extract.py 文件头（一条 0x4C7 = 一个文本框 = 一次点击）
附加过滤：系统/UI（章ジャンプ表、ミニゲーム説明「チュートリアル」区段、调试标签）
"""
import sys, os, glob, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kedamono_ns_extract as E

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, '提取结果', '[NS-JP]猛獣使いと王子様 ～Flower ＆ Snow～ for Nintendo Switch.txt')
TUTO = re.compile(r'チュートリアルへようこそ|^【新要素|^【ストーリーセレクト.*チュートリアル')
DEV = re.compile(r'^【分岐用')
UI = re.compile(r'ボタン|スティック|タッチ操作|カーソル|ポップアップ|モフモフ|連打')
SYS = re.compile(r'開放されました|Ｎｅｗ　Ｓｃｅｎａｒｉｏ')


def drop_tutorial(rows):
    out, i, n = [], 0, len(rows)
    while i < n:
        if TUTO.search(rows[i]):
            j = i + 1
            while j < n and not rows[j].startswith(('\u300c', '\uff08')):
                j += 1
            i = j
            continue
        out.append(rows[i])
        i += 1
    return out


def drop_ui_runs(rows):
    """连续行内若 >=3 行含操作词（操作说明），整段剔除；段内允许夹 1 行无关键词。"""
    flag = [bool(UI.search(r)) for r in rows]
    out, i, n = [], 0, len(rows)
    while i < n:
        if not flag[i]:
            out.append(rows[i]); i += 1; continue
        j = last = i
        while j < n:
            if flag[j]:
                last = j
            elif j - last > 1:
                break
            j += 1
        j = last + 1
        if sum(flag[i:j]) >= 3:
            i = j
            continue
        out.extend(rows[i:j])
        i = j
    return out


def main():
    files = []
    for sub, pri in (('k1/script', 0), ('k2/SCRIPT', 1)):
        for p in glob.glob(os.path.join(ROOT, '_w_kedamono', sub, '*')):
            nm = os.path.basename(p)
            if not nm.isdigit():
                continue
            files.append((pri, int(nm), p))
    files.sort()
    rows = []
    for pri, num, p in files:
        r, _, _ = E.extract(p)
        rows.extend(r)
    rows = [r for r in rows if not DEV.search(r)]
    rows = drop_tutorial(rows)
    rows = drop_ui_runs(rows)
    rows = [r for r in rows if not SYS.search(r)]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(rows) + '\n')
    print('rows', len(rows), '->', OUT)


if __name__ == '__main__':
    main()
