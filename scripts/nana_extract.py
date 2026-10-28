#!/usr/bin/env python3
"""nana_extract.py -- [PS2-JP] NANA -ナナ- text extractor.

Source chain (verified 2026-10-23):
  ISO9660 -> STORY/ALLSC.NKP (Konami NKP archive) -> 1092 x <名>.nkp (NKP)
          -> 1 x *.cg  = PLAIN TEXT Konami EVS script (cp932, CRLF, TAB indent)
Text ops:
  MSGN <voice> "<name>" "<text>"          normal line (separate name window)
  MSG ( 0 ) "<text>"                      mail body (no name window)
  MSGD <voice> ( Gx ) "<text>"            mail/phone body with runtime voice slot
  EVTSELMSGN ( n ) ( m ) <voice> "<name>" "<prompt>" "<opt>"*n   -> prompt + n options
  TELSELMSGN ( n ) <voice> "<text>"       phone prompt (n = 0 in this game)
Codes:
  '\\u2460\\uff4e' = in-box line break (merge; max 1 per op => 2-line window)
  '\\u2460\\uff33<digit>' = runtime slot; 内容由 SETSTR ( kind ) ( slot ) 绑定（见 SLOT_ROLE）
  '\\u2461' '\\u2462' = end-of-line icon codes -> strip

SETSTR 第 1 参数＝字串域（2=場所 / 3=日付 / 4=時間帯），第 2 参数＝①Ｓ 的槽号。
槽值来自存储数据（GETDATA）或 CHDATE 的玩家选择，静态无解 ⇒ 按域出〔日付〕等标注。
域依据：脚本内联注释 `// G0 int day` `// G1 int time` `// G2 int place`；
SLPM_659.14 0x24EBC0-0x24EC48 的 8 B/槽串池＝13 個地名 ＋ 月/日 ＋ 昼/夕方/夜。
"""
import os
import re
import sys

UNRES = '〔未解析〕'
SLOT_ROLE = {'2': '場所', '3': '日付', '4': '時間帯'}

RE_MSGN = re.compile(r'^MSGN\s+(?:\([^)]*\)|\S+)\s+"([^"]*)"\s+"([^"]*)"$')
RE_MSG = re.compile(r'^MSG\s+\(\s*\d+\s*\)\s+"([^"]*)"$')
RE_MSGD = re.compile(r'^MSGD\s+\S+\s+\([^)]*\)\s+"([^"]*)"$')
RE_SEL = re.compile(r'^EVTSELMSGN\s+\(\s*(\d+)\s*\)\s+\(\s*\d+\s*\)\s+\S+\s+(.*)$')
RE_TELSEL = re.compile(r'^TELSELMSGN\s+\(\s*\d+\s*\)\s+\S+\s+"([^"]*)"$')
RE_SETSTR = re.compile(r'^SETSTR\s+\(\s*(\d+)\s*\)\s+\(\s*(\d+)\s*\)')


def clean(t, slots=None):
    slots = slots or {}

    def _slot(m):
        d = m.group(1)
        if d in '０１２３４５６７８９':
            d = str(ord(d) - 0xFF10)
        return '〔%s〕' % SLOT_ROLE.get(slots.get(d), '未解析')

    t = re.sub('①Ｓ([0-9０-９])', _slot, t)
    t = t.replace('①正', '正')
    t = t.replace('①ｎ', '')      # 框内换行＝排版换行，直接合并（一次点击＝一行）
    t = re.sub('[②③]', '', t)
    return t.strip()


def expand(seq):
    """一次点击 = 一行：框内换行（①ｎ）是排版换行，合并进同一行，不拆。"""
    return [t.replace('\x01', '') for t in seq]


def parse(path):
    out = []
    slots = {}
    with open(path, encoding='cp932', errors='replace') as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith('@') or s.startswith('//'):
                continue
            m = RE_SETSTR.match(s)
            if m:
                slots[m.group(2)] = m.group(1)
                continue
            m = RE_MSGN.match(s)
            if m:
                out.append(clean(m.group(2), slots))
                continue
            m = RE_MSG.match(s) or RE_MSGD.match(s) or RE_TELSEL.match(s)
            if m:
                out.append(clean(m.group(1), slots))
                continue
            m = RE_SEL.match(s)
            if m:
                n = int(m.group(1))
                strs = re.findall(r'"([^"]*)"', m.group(2))
                prompt = clean(strs[1], slots) if len(strs) > 1 else ''
                if prompt:
                    out.append(prompt)
                for opt in strs[2:2 + n]:
                    o = clean(opt, slots)
                    if o:
                        out.append(o)
    return [x for x in out if x]


def order_from_slpm(path):
    d = open(path, 'rb').read()
    paths = [m.decode() for m in
             re.findall(rb'script/(?:[a-zA-Z_]+)/[A-Za-z0-9_\-]+\.nc', d)]
    seen = []
    for p in paths:
        b = os.path.basename(p)[:-3]
        if b not in seen:
            seen.append(b)
    return seen


def trim_common(lines, emitted, win, k=8):
    """ルート別ファイルの共通導入部／共通終結部を落とす。
    既出の並びと先頭 k 行が一致すれば、一致が途切れるまで先頭を削る（末尾も同様）。
    内部の重複は触らない（場面の連続性を壊さないため）。"""
    n = len(lines)
    if n >= k:
        best = 0
        for j in win.get(tuple(lines[:k]), ()):
            m = k
            while m < n and j + m < len(emitted) and lines[m] == emitted[j + m]:
                m += 1
            best = max(best, m)
        lines = lines[best:]
    n = len(lines)
    if n >= k:
        best = 0
        for j in win.get(tuple(lines[-k:]), ()):
            m = k
            while m < n and j - m >= 0 and lines[n - 1 - m] == emitted[j - 1 - m]:
                m += 1
            best = max(best, m)
        lines = lines[:n - best]
    return lines


def drop_known_runs(lines, emitted, win, k=12, kw=8):
    """既出の並びと k 行以上連続一致する内部ブロックを落とす（丸ごと複製された共通イベント対策）。
    win は kw 行窓の索引。"""
    out = []
    i = 0
    n = len(lines)
    while i < n:
        if i + kw <= n:
            hit = 0
            for j in win.get(tuple(lines[i:i + kw]), ()):
                m = kw
                while i + m < n and j + m < len(emitted) and lines[i + m] == emitted[j + m]:
                    m += 1
                hit = max(hit, m)
            if hit >= k:
                i += hit
                continue
        out.append(lines[i])
        i += 1
    return out


def add_windows(lines, win, start, k=8):
    for i in range(max(0, start - k + 1), len(lines) - k + 1):
        win.setdefault(tuple(lines[i:i + k]), []).append(i)


def main():
    scr, out, slpm = sys.argv[1], sys.argv[2], sys.argv[3]
    files = {}
    for fn in os.listdir(scr):
        if not fn.endswith('.cg'):
            continue
        base = fn[:-3]
        stem = base.split('_A-')[0] if '_A-' in base else (
            base.split('_evt_')[0] if '_evt_' in base else base)
        files[stem] = os.path.join(scr, fn)
    order = [b for b in order_from_slpm(slpm) if b in files]
    rest = sorted(set(files) - set(order))
    keys = order + rest

    seen = set()
    lines = []
    win = {}
    used = 0
    trimmed = 0
    for k in keys:
        ls = parse(files[k])
        if not ls:
            continue
        key = '\n'.join(ls)
        if key in seen:
            continue
        seen.add(key)
        used += 1
        ls2 = trim_common(ls, lines, win)
        ls2 = drop_known_runs(ls2, lines, win)
        trimmed += len(ls) - len(ls2)
        start = len(lines)
        lines.extend(expand(ls2))
        add_windows(lines, win, start)
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('files', len(keys), 'used', used, 'trimmed', trimmed, 'lines', len(lines))


if __name__ == '__main__':
    main()
