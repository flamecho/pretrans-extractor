#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""忍び、恋うつつ for Nintendo Switch —— 成品构建。

链路：XCI -> NCA -> RomFS/CONTENTS/STORY_01(本編)/STORY_02(雪月花恋絵巻).cpk
      -> SCRIPT/*.DAT (STCM2L/UTF-8) + SYSTEM.cpk/DATABASE/dbDictionary.gbin (用語辞典)
成行：见 scripts/shinobi_ns_extract.py 文件头（0x1F4=一次点击；框内软换行合并）
附加过滤：系统/UI 确认串、章ジャンプ表、教程块
"""
import sys, os, glob, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shinobi_ns_extract as E

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT = os.path.join(ROOT, '_w_shinobi', 'sys', 'DATABASE', 'dbDictionary.gbin')
OUT = os.path.join(ROOT, '提取结果', '[NS-JP]忍び、恋うつつ for Nintendo Switch.txt')

UI = re.compile(r'モード|選択肢|ゲージ|ボタン|好感度|数値|設定してあります|※')
QUOTES = '\u300c\u300d\u300e\u300f\uff08\uff09'


def drop_ui_blocks(rows):
    """连续 >=3 行、全无引号、且 >=2 行含 UI 词 ⇒ 判为玩法说明块，整段剔除。"""
    out, i, n = [], 0, len(rows)
    while i < n:
        if any(c in rows[i] for c in QUOTES):
            out.append(rows[i]); i += 1; continue
        j = i
        while j < n and not any(c in rows[j] for c in QUOTES):
            j += 1
        run = rows[i:j]
        if len(run) >= 3 and sum(1 for r in run if UI.search(r)) >= 2:
            i = j
            continue
        out.extend(run)
        i = j
    return out


def glossary():
    d = open(DICT, 'rb').read()
    ss, cur = [], bytearray()
    for b in d:
        if b == 0:
            if cur:
                ss.append(cur.decode('utf-8', 'replace'))
                cur = bytearray()
        else:
            cur.append(b)
    out = []
    for k, s in enumerate(ss):
        if re.fullmatch(r'yougo_\d+', s):
            head, desc = ss[k + 1], ss[k + 3]
            out.append('【%s】%s' % (head, desc.replace('#n', '')))
    return out


def main():
    files = []
    for sub, pri in (('s1', 0), ('s2', 1)):
        d = os.path.join(ROOT, '_w_shinobi', sub, 'SCRIPT')
        for p in glob.glob(os.path.join(d, '*.DAT')):
            nm = os.path.basename(p)[:-4]
            if not nm.isdigit():
                continue
            files.append((pri, int(nm), p))
    files.sort()
    rows = []
    for pri, num, p in files:
        r, _, _, _ = E.extract(p)
        rows.extend(r)
    rows = drop_ui_blocks(rows)
    g = glossary()
    rows.extend(g)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(rows) + '\n')
    print('rows', len(rows), 'glossary', len(g), '->', OUT)


if __name__ == '__main__':
    main()
