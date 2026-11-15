# -*- coding: utf-8 -*-
"""[NS-JP] Code：Realize ～白銀の奇跡～ for Nintendo Switch —— Utage（宴）剧本提取

## 容器链
  romfs/Data/StreamingAssets/Adv/Switch/adv.scenarios.asset   （UnityFS 2019.2.12f1，3.6 MB）
    = 16 个 MonoBehaviour：`.book`（剧本）/`.chapter`（章节表）/`Adv.scenarios`（章节入口）
  romfs/Data/StreamingAssets/Cpk/Database.cpk                 （CRI CPK）
    → Adv/DictionaryDatabase.json（用語辞典 112 条）

## 记录框架（L0）
  Utage `.book` 的 MonoBehaviour 字段（UnityPy typetree 直读）：
    `importVersion` + `importGridList`（= 每章 sheet）
    sheet = { rows, name, type, textLength, headerRow, entityIndexTbl, entityDataList }
    row   = { rowIndex, strings[] }，`strings[0]` = 命令名，表头行给出列名
  实测列：`Command, Arg1..Arg6, WaitType, Text, PageCtrl, Voice, WindowType`

## 成行（L0）
  **一条 `Text` 命令 = 一个文本框 = 一次点击 ⇒ 一行**（21,336 条）。
  格内 `\\n`（字面反斜杠 + n）= 框内排版换行 ⇒ 合并。
  `Selection` 行 = 选项，选项文本同在第 8 列（`sureN` 在 Arg1，是跳转标号不是文本）。
  Arg1（Text 行）= 名字窗内容 ⇒ **独立名字窗，整列剔除**。
  `<param=player_name>` → 默认名 **カルディア**（定值依据：420 条宏版里有 248 条替换后与语料中
  既有字面行逐字相同；换其它候选名命中 0）。

## 不给
  `DebugMode.book`（デバッグモード 菜单）、Replay/Subroutine/Thred/Macro/ParamTable/Start/Adv
  （系统脚本，无正文）
"""
import argparse
import json
import os
import re
import sys

import UnityPy

TEXT_CMD = 'Text'
SEL_CMD = 'Selection'
HERO = 'カルディア'
MACRO = re.compile(r'<\s*param\s*=\s*([^>]*?)\s*>')
COLOR = re.compile(r'</?color[^>]*>')
SKIP_BOOKS = {'DebugMode.book'}


def clean(t):
    t = t.replace('\\n', '\n')
    t = MACRO.sub(HERO, t)
    t = COLOR.sub('', t)
    t = t.replace('\n', '')                 # 框内软换行 ⇒ 合并
    t = t.replace('\u3000', ' ')
    return re.sub(r'[ \t]+', ' ', t).strip()


def book_rows(tt, cnt=None):
    """一个 .book → 逐行文本（含选项），按 sheet 顺序。"""
    out = []
    for sh in tt.get('importGridList') or []:
        rows = sh['rows']
        hr = sh.get('headerRow', 0)
        if not rows or hr >= len(rows):
            continue
        hdr = [c.strip() for c in rows[hr]['strings']]
        if 'Text' not in hdr:
            continue
        ti = hdr.index('Text')
        for r in rows[hr + 1:]:
            cs = r['strings']
            if not cs:
                continue
            cmd = cs[0]
            if cmd != TEXT_CMD and cmd != SEL_CMD:
                continue
            if ti >= len(cs):
                continue
            t = clean(cs[ti])
            if t:
                out.append((raw_norm(cs[ti]), t))
                if cmd == SEL_CMD and cnt is not None:
                    cnt[0] += 1
    return out


def raw_norm(t):
    return t.replace('\\n', '').replace('\u3000', ' ').strip()


def dedup(pairs):
    """相邻「同一句的两种写法」→ 只留一条。判据用**原始格**：
    · 原始格规范化后完全相同 ⇒ **两条都留**（源真的连写两次，如 `「…………」` ×2）；
    · 原文不同、只有 `<param>` 名字写法不同（`愛してるぜ、カルディア。` / `愛してるぜ、<param=player_name>。`）⇒ 删后一条。"""
    res, prev_raw = [], None
    for raw, t in pairs:
        if res and prev_raw is not None and raw != prev_raw and res[-1] == t:
            continue                      # 只差名字写法 ⇒ 变体对
        res.append(t)
        prev_raw = raw
    return res


def load_dict(path):
    d = json.load(open(path, encoding='utf-8'))
    rows = []
    for e in d['param']:
        name = (e.get('name') or '').strip('\u3000 ')
        text = (e.get('explain') or '').replace('#n', '')
        text = re.sub(r'#[A-Za-z]+\[[^\]]*\]', '', text).replace('\u3000', ' ').strip()
        if name and text:
            rows.append('【%s】%s' % (name, text))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--asset', required=True)
    ap.add_argument('--dict', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--json')
    a = ap.parse_args()

    env = UnityPy.load(a.asset)
    books, order = {}, None
    for o in env.objects:
        if o.type.name != 'MonoBehaviour':
            continue
        tt = o.read_typetree()
        nm = tt.get('m_Name', '')
        if nm == 'Boot.chapter':
            order = [d['m_PathID'] for d in tt['dataList']]
        if 'importGridList' in tt and nm.endswith('.book'):
            books[o.path_id] = (nm, tt)

    seq = [books[i] for i in order if i in books] if order else sorted(books.values())
    lines, stat = [], {}
    opt = [0]
    for nm, tt in seq:
        if nm in SKIP_BOOKS:
            stat[nm] = 'skip'
            continue
        rows = dedup(book_rows(tt, opt))
        stat[nm] = len(rows)
        lines.extend(rows)

    n_body = len(lines)
    dct = load_dict(a.dict)
    lines.extend(dct)

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    for k, v in stat.items():
        print('  %-24s %s' % (k, v))
    print('书籍顺序: %s' % [n for n, _ in seq])
    print('其中选项 %d 条（去重前）' % opt[0])
    print('正文 %d 行 + 用語辞典 %d 条 = %d 行 -> %s' % (n_body, len(dct), len(lines), a.out))
    if a.json:
        json.dump({'stat': stat, 'lines': lines}, open(a.json, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)


if __name__ == '__main__':
    sys.exit(main())
