#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Friendly lab - unlock();（Tennenouji / Unity 2021）→ 一台本一台词框的正文。

载体（L0）
  · Unity 2021.3.22f1 构建；正文全在 **一个 TextAsset**：`package_unity/scriptdatas`（14,470,765 B），
    以 `UnityFS` AssetBundle 存放（同一 bundle 里还有 `scriptpoints` / `system` / `version` 三个 TextAsset）。
  · 脚本是**行式 DSL**（UTF-8）：
      `__` ＋ 下一行 `__<场景ID>`  ＝ 场景开始（691 个）
      `@@<命令>{<JSON>}`           ＝ 引擎命令（18 种：image / alphafade / message / layervisible / wait / se …）
      `//…`                        ＝ 注释（含 `//［ 名字 || MsgId_xxx ］//` 这种作者留的名字回显）
      `\\t<行>`                      ＝ **上一个 `@@message` 的框内文本行**（`0x0A` 排版换行）
  · **断框判据（L0）**：`@@message{…}` ＝ 一个文本框 ＝ 一次点击；其后连续的 `\\t` 行是框内换行 ⇒ 合并。
    自证：`@@message` 23,290 处 ／ `\\t` 段也是 23,290 段（1:1），每段后恰接空行（23,289）或下一条命令（1）。
  · `append:true`（5 处）＝ **接在同一框后面**（不新开框）⇒ 与前一框合并。
  · `noTextWait:true`（316 处）＝ 打字机动画不等（仍是一次点击，文本照样上屏）⇒ 仍各占一行。

名字（S6-lines-names）
  `@@message` 的 `charName` / `label` 是**独立字段**，与 `target`（message_left / message_right / …）无关，
  框内文本里没有名字 ⇒ **独立名字窗，剔除**（不写入正文）。

替换槽
  `:{WordNO_NN,<n>,<默认文本>}` ＝ 玩家提问时登记的「ワード」插入槽，共 2,663 处 / 319 种形态；
  脚本自带**字面默认值**（第三参数，如 `:{WordNO_04,1,お母さん}` ⇒ `お母さん`）⇒ 用默认值，不猜、不留占位。

用法
  python scripts/unity_scriptdatas_text.py <scriptdatas 文件> <out.txt> [--order db_action.json] [--stat]
"""
import argparse
import io
import json
import re

TAB = '\t'
PLACEHOLDER = re.compile(r':\{WordNO_\d+,\s*\d+,\s*([^}]*)\}')
CMD = re.compile(r'^@@(\w+)\{')


def scenes(lines):
    """→ [(scene_id, start_index, end_index)]；场景头＝`__` 行＋下一行 `__<id>`。

    ⚠ 文件**第一行就是 `__<id>`**（没有前导 `__`）—— 首场景要单独认，否则整场丢。
    """
    out = []
    i, n = 0, len(lines)
    if n and lines[0].startswith('__') and lines[0].strip() != '__':
        out.append((lines[0][2:].strip(), 1))
    while i < n:
        if lines[i].strip() == '__' and i + 1 < n and lines[i + 1].startswith('__'):
            sid = lines[i + 1][2:].strip()
            if sid:
                out.append((sid, i + 2))
        i += 1
    for k, (sid, st) in enumerate(out):
        out[k] = (sid, st, out[k + 1][1] if k + 1 < len(out) else n)
    return out


def join_box(parts):
    """框内行合并：日文直接相接（排版换行）；**两侧都是拉丁字母/数字时补一个半角空格**
    （否则 `has no end of a tail` ＋ `because…` 会粘成 `tailbecause`）。"""
    out = ''
    for s in parts:
        if out and re.search(r'[0-9A-Za-z]$', out) and re.match(r'[0-9A-Za-z]', s):
            out += ' '
        out += s
    return out


def parse_boxes(lines, lo, hi):
    """场景 [lo,hi) 内的文本框 → [(messageId, charName, text)]（append 已合并）。"""
    out = []
    i = lo
    while i < hi:
        line = lines[i]
        if not line.startswith('@@message'):
            i += 1
            continue
        try:
            meta = json.loads(line[len('@@message'):])
        except json.JSONDecodeError:
            i += 1
            continue
        body = []
        j = i + 1
        while j < hi and lines[j].startswith(TAB):
            body.append(lines[j][1:].rstrip())
            j += 1
        text = join_box(body).strip()
        if text:
            text = PLACEHOLDER.sub(lambda m: m.group(1).strip(), text)
            if meta.get('append') and out:
                pid, pname, ptext = out[-1]
                out[-1] = (pid, pname, ptext + text)
            else:
                out.append((meta.get('messageId', ''), meta.get('charName', ''), text))
        i = j
    return out


def order_key(sid):
    """场景分组顺序（本作非线性：按场景 ID 分组，ID 自带 day_NN_xx 序号）。"""
    head = ('opening', 'start', 'clothchange00_firstpajama', 'clothchange01_beforebed',
            'clothchange02_firstmorningafter', 'clothchange03_morningafter', 'movie_op', 'room')
    if sid in head:
        return (0, head.index(sid), sid)
    m = re.match(r'^day_(\d+)_', sid)
    if m:
        return (1, int(m.group(1)), sid)
    m = re.match(r'^card_(\d+)', sid)
    if m:
        return (2, int(m.group(1)), sid)
    m = re.match(r'^sa_', sid)
    if m:
        return (3, 0, sid)
    if sid.startswith('ending'):
        return (4, 0, sid)
    if sid.startswith('end_'):
        return (5, 0, sid)
    return (6, 0, sid)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('out')
    ap.add_argument('--order', help='database/action 的 JSON（仅用于报告核对，不影响成行）')
    ap.add_argument('--stat', action='store_true')
    a = ap.parse_args()

    text = io.open(a.src, encoding='utf-8').read()
    lines = text.split('\n')
    sc = scenes(lines)
    # 归并：一个场景可能被拆成多段（同一 ID 不重复出现，脚本实测）
    rows = []
    st = {'scene': 0, 'box': 0, 'append': 0, 'term': 0}
    for sid, lo, hi in sc:
        boxes = parse_boxes(lines, lo, hi)
        st['scene'] += 1
        st['box'] += len(boxes)
        rows.extend((sid, mid, name, t) for mid, name, t in boxes)
    rows.sort(key=lambda r: order_key(r[0]))
    with io.open(a.out, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(r[3] for r in rows) + '\n')
    if a.stat:
        import collections
        per = collections.Counter(r[0] for r in rows)
        print('场景 %d（有正文 %d）／文本框 %d 行 / %d 字'
              % (st['scene'], len(per), len(rows), sum(len(r[3]) for r in rows)))
        print('名字种数 %d：%s' % (len(set(r[2] for r in rows)),
                                 collections.Counter(r[2] for r in rows).most_common(8)))
        print('场景分组', collections.Counter(order_key(r[0])[0] for r in rows))
        json.dump([[r[0], r[1], r[2]] for r in rows], open(a.out + '.index.json', 'w'),
                  ensure_ascii=False)


if __name__ == '__main__':
    main()
