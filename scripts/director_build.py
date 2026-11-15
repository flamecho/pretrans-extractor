#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
King of Beast 成品构建器
=======================
读取 director_text.extract_file 的提取结果，按 skill 口径清洗并落盘：
  - 排除 character.cxt（二进制乱码误判）
  - system.dxr 仅排除纯系统 UI（存档/读取/退出/提示），保留日程叙事
  - g_over.dxr 排除 UI 提示
  - 文本框内换行 \r 已在 extract 阶段转空格；此处二进制写出纯 LF + BOM
用法: python director_build.py <data_dir> <out_txt>
"""
import os, sys, re, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from director_text import extract_file

EXCLUDE_FILES = {"character.cxt"}
SYSTEM_UI = {
    "さてと、今日 1日のスケジュールを決めなきゃ…\r\r※MAPのアイコンをクリックして行動を決めます\r",
    "さてと、今日 1日のスケジュールを決めなきゃ…\r\r※引き続き夜間の行動を決めて下さい\r",
    "さてと、今日 1日のスケジュールを決めなきゃ…\r\r※スケジュールはこれでOKですか？\r",
    "ゲームを終了しますか？\r自動保存されませんのでご注意ください！！",
    "データをセーブする場所を選んでください。\rキャンセルする場合はEXITボタンを押してください。",
    "セーブが完了しました。",
    "データをロードする場所を選んでください。\rキャンセルする場合はEXITボタンを押してください。",
    "ロードが完了しました。",
}
GAME_OVER_UI = {"画面をクリックするとタイトル画面に戻ります"}


def build(data_dir, out_txt):
    collected = []  # (file, text)
    per_file = {}
    for fn in sorted(os.listdir(data_dir)):
        if not fn.lower().endswith(('.dxr', '.cxt', '.cst')):
            continue
        lines = extract_file(os.path.join(data_dir, fn))
        per_file[fn] = len(lines)
        for s in lines:
            if fn in EXCLUDE_FILES:
                continue
            if fn == "system.dxr" and s in SYSTEM_UI:
                continue
            if fn == "g_over.dxr" and s in GAME_OVER_UI:
                continue
            if s:
                collected.append((fn, s))
    # 去重（保留首次出现顺序）
    seen = set()
    uniq = []
    for fn, s in collected:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    # 二进制写出：UTF-8 BOM + 纯 LF
    os.makedirs(os.path.dirname(out_txt), exist_ok=True)
    with open(out_txt, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(("\n".join(uniq)).encode('utf-8'))
        f.write(b'\n')
    # 排除清单
    excl = os.path.join(os.path.dirname(out_txt), '..', '_work_kob', 'excluded.txt')
    with open(excl, 'w', encoding='utf-8') as f:
        for fn in sorted(os.listdir(data_dir)):
            pass
    print("per_file:", per_file)
    print("TOTAL unique lines:", len(uniq))
    return uniq, per_file


if __name__ == '__main__':
    data_dir = sys.argv[1]
    out_txt = sys.argv[2]
    build(data_dir, out_txt)
