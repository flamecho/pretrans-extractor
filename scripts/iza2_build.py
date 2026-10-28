#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""いざ、出陣！恋戦 第二幕 ～甲斐編～ —— 按 scenelist 顺序组装全文本。

输入：dec/<storage>.json（PsbDecompile 产出）、dec/scenelist.json（master 顺序表）
输出：提取结果/[PSP-JP]いざ、出陣！恋戦 第二幕 甲斐編_全文本.txt
"""
import io
import json
import os
import re
import sys

ROOT = (os.path.abspath(sys.argv[1]) if len(sys.argv) > 1
        else os.path.dirname(os.path.abspath(__file__)))
DEC = os.path.join(ROOT, 'dec')
OUT = os.path.join(ROOT, '提取结果',
                   '[PSP-JP]いざ、出陣！恋戦 第二幕 甲斐編_全文本.txt')

NAME = '華'          # $playerName; 的默认名（御柳家の華姫 ⇒ 宏=名）
SKIP_STORAGE = {
    'test.ks',              # 開発テスト
    '00_com_sys.txt',       # 立ち絵（表情・衣装）素材ビューア
    '00_com_sys_kai.txt',   # 音声テスト一覧
}

_cache = {}


def load_scene(storage, target):
    if storage not in _cache:
        p = os.path.join(DEC, storage + '.json')
        _cache[storage] = json.load(open(p, encoding='utf-8-sig')) if os.path.exists(p) else None
    j = _cache[storage]
    if not j:
        return None
    for sc in j.get('scenes') or []:
        if sc.get('label') == target:
            return sc
    return None


def clean(s):
    s = s.replace('$playerName;', NAME)
    s = s.replace('\r', '')
    # 框内软换行 → 合并（原文为 \n）
    s = s.replace('\n', '')
    return s.strip()


def is_internal_selects(e):
    """章間 这类自动分支（整组同一文本，或只有一条）不是玩家可见选项。"""
    sel = e.get('selects') or []
    if not sel:
        return True
    return len({x.get('text') for x in sel}) == 1


def main():
    lst = json.load(open(os.path.join(DEC, 'scenelist.json'), encoding='utf-8-sig'))['list']
    lines = []
    stat = {'entries': 0, 'scene_missing': 0, 'texts': 0, 'selects': 0,
            'tc_sum': 0, 'sel_entries': 0, 'dup_sel': 0, 'internal_sel': 0}
    missing = []

    for e in lst:
        storage, target = e['storage'], e['target']
        if storage in SKIP_STORAGE:
            continue
        stat['entries'] += 1
        stat['tc_sum'] += e.get('textCount') or 0
        sc = load_scene(storage, target)
        if sc is None:
            stat['scene_missing'] += 1
            missing.append((storage, target))
            continue

        for t in sc.get('texts') or []:
            if not (isinstance(t, list) and len(t) > 2 and isinstance(t[2], str)):
                continue
            s = clean(t[2])
            if s:
                lines.append(s)
                stat['texts'] += 1

        sel = e.get('selects') or []
        if sel:
            stat['sel_entries'] += 1
            if is_internal_selects(e):
                stat['internal_sel'] += len(sel)
            else:
                seen = set()
                for x in sel:
                    s = clean(x.get('text') or '')
                    if not s:
                        continue
                    if s in seen:
                        stat['dup_sel'] += 1
                        continue
                    seen.add(s)
                    lines.append(s)
                    stat['selects'] += 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')

    exp = stat['tc_sum'] - stat['sel_entries']
    print(json.dumps(stat, ensure_ascii=False))
    print('expected texts =', exp, ' actual =', stat['texts'],
          ' diff =', stat['texts'] - exp)
    print('lines =', len(lines))
    if missing:
        print('missing scenes', len(missing), missing[:10])


if __name__ == '__main__':
    main()
