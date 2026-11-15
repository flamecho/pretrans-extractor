#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[JP]イカレちんぽ屋（TVP/KiriKiri + KAG3）→ 一次点击＝一行。

L0 判据（scenario1/2, end1/2）：
  * `[np]` 宏（macro.ks: `[p][cm][cm][label]`）＝ 页结束 + 点击 ⇒ 页界
  * `[l]` ＝ 页内「改行してクリック待ち」⇒ 同一页的再点击 ⇒ 双版（段行 + 整页行）
  * `[r]` ＝ 显示换行（软换行，合并）
  * `[cm]`/`[ct]`/`[er]`＝清屏（无点击）= 页界；`[waitclick]`＝点击等待（结局画面，无文本）
  * `[indent]`/`[endindent]`/`[graph]`/`[hr]`/`[wait]`/`[wt]`/`[s]`/`[image]`/`[layopt]`/
    `[position]`/`[locate]`/`[current]`/`[title]`/`[clickskip]`/`[playse]`/`[bgmopt]`/…＝非文本标签，剥
  * `[button graphic=…]`＝图片式选项（无字）⇒ 跳过
  * `【名前】` 印在正文文本框内（无 `[name]` 独立名字窗）⇒ 保留并接在同一行台词前

用法：python scripts/ikare_text.py <scenario 目录> --out 成品.txt [--stat]
"""
import argparse
import os
import re
import sys

TAG = re.compile(r'\[[^\]]*\]')
WS = '\u3000 '

SKIP_TAGS = {
    'indent', 'endindent', 'graph', 'hr', 'wait', 'wt', 's', 'image', 'layopt',
    'position', 'locate', 'current', 'title', 'clickskip', 'playse', 'stopse',
    'playbgm', 'stopbgm', 'fadeoutbgm', 'fadeoutse', 'fadeinse', 'bgmopt', 'seopt',
    'quake', 'trans', 'trans0', 'trans1', 'trans2', 'trans3', 'zinobun', 'textbox',
    'nobox', 'eval', 'if', 'endif', 'jump', 'call', 'return', 'button', 'label',
    'macro', 'endmacro', 'clickskip', 'loadplugin', 'set', 'rclick', 'save',
    'video', 'movie', 'seopt', 'autolabel',
}
CLICK_L = 'l'
PAGE_TAGS = {'np', 'p', 'cm', 'ct', 'er', 'waitclick'}


def tag_name(tok):
    return tok[1:].split(None, 1)[0].rstrip(']').lower() if tok.startswith('[') else ''


def parse_file(path):
    """返回 [(page_id, [seg1, seg2, ...])]；seg 已合并 [r] 软换行。"""
    raw = open(path, 'rb').read().decode('cp932', 'replace')
    pages = []
    segs = []
    cur = []

    def flush_seg():
        s = ''.join(cur).replace('\r', '').strip(WS)
        cur.clear()
        if s:
            segs.append(s)

    def flush_page():
        flush_seg()
        if segs:
            pages.append((os.path.basename(path), list(segs)))
        segs.clear()

    for line in raw.split('\n'):
        s = line.strip()
        if not s or s.startswith(';') or s.startswith('//') or s.startswith('*'):
            continue
        # 整行按标签切
        pos = 0
        for m in TAG.finditer(line):
            txt = line[pos:m.start()]
            if txt:
                cur.append(txt)
            tok = m.group(0)
            name = tag_name(tok)
            if name == 'r':
                pass  # 软换行 ⇒ 直接合并
            elif name == 'l':
                flush_seg()
            elif name in PAGE_TAGS:
                flush_page()
            elif name == 'np':
                flush_page()
            else:
                # 其余标签一律剔除；按钮等无文本
                pass
            pos = m.end()
        tail = line[pos:]
        if tail:
            cur.append(tail)
        # 行末换行：KAG 源码换行不产生显示换行（需 [r]/[l]），故不处理
    flush_page()
    return pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('--out', required=True)
    ap.add_argument('--stat', action='store_true')
    a = ap.parse_args()
    order = ['scenario1.ks', 'scenario2.ks', 'end1.ks', 'end2.ks']
    rows = []
    st = {'pages': 0, 'dual': 0, 'segs': 0, 'lines': 0}
    for fn in order:
        for _, segs in parse_file(os.path.join(a.root, fn)):
            st['pages'] += 1
            st['segs'] += len(segs)
            if len(segs) >= 2:
                st['dual'] += 1
                for s in segs:
                    rows.append(s)
                rows.append(''.join(segs))
            else:
                rows.append(segs[0])
            st['lines'] += len(segs) if len(segs) >= 2 else 1
    with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(rows) + '\n')
    print(st, '→', a.out, len(rows), '行', sum(map(len, rows)), '字')


if __name__ == '__main__':
    main()
