#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FORIS-OS（0verflow 系／S.S.D.S. 等）剧本 XML → 一次点击一行的正文。

前置：`python scripts/foris_pack.py x <PACK/SCRIPT.CMP> <dir>` 解出 `*.XML`（22 个）。

剧本是**编译后的 XML**（UTF-8），引擎用 Xerces 解析（`SCRIPT.mod` 里有 xerces 符号）：

  <SCRIPT>
  <BLOCK label="S1-S1">
    <FUNCTION name="MESSAGE"/>            ← **显示一个文本框 ＝ 一次点击**
    <RESOURCE no="0">                     ← 紧挨在命令**前面**的资源块
      <CREATE type="INT">0</CREATE>       ← 固定 0（资源类型）
      <CREATE type="GSCRIPT">0</CREATE>   ← 脚本内序号
      <CREATE type="STR">す、すごい大きいなぁ</CREATE>   ← **正文**
      <CREATE type="INT">0</CREATE>       ← 语音号
      <CREATE type="INT">1</CREATE>       ← 表情号
      <CREATE type="STR">S1_000</CREATE>  ← 消息 ID
    </RESOURCE>
    <RESOURCE no="21">                    ← 选项资源：INT ＋ N×(GSCRIPT, STR)
      <CREATE type="INT">1</CREATE>
      <CREATE type="GSCRIPT">21</CREATE><CREATE type="STR">はい、気をつけます</CREATE>
      <CREATE type="GSCRIPT">22</CREATE><CREATE type="STR">いえ、でも僕、人を信じて…</CREATE>
    </RESOURCE>
    <FUNCTION name="SELECT">…</FUNCTION>  ← 选项：**每条 STR 一行**
  </BLOCK>

断框判据（L0）：`FUNCTION name="MESSAGE"` ＝ 一个 message 框 ＝ 一次点击；正文是该框**前一兄弟** `RESOURCE`
的第 3 个 `CREATE`。**文本内没有换行码**（7,133 条里 0 个 `\\n`）⇒ 无需框内合并。
`FUNCTION name="SELECT"` 的选项文本同样取前一兄弟 `RESOURCE` 的 `STR`，一条一行。

名字：`MESSAGE` 只有 `INT(语音号)/INT(表情号)`，**没有名字字段**，名字由 `LOADCHAR` / 名字窗另画 ⇒ 正文里不含名字，无需剔除。

用法
  python scripts/foris_script_xml.py <解出的 XML 目录> <out.txt> [--order S1,S2,…] [--stat]
"""
import argparse
import glob
import io
import os
import re
import xml.etree.ElementTree as ET


def kids(el):
    return list(el)


def walk(el, cb):
    """按文档顺序遍历，回调 (elem, next_sibling)。"""
    ch = list(el)
    for i, c in enumerate(ch):
        cb(c, ch[i + 1] if i + 1 < len(ch) else None)
        walk(c, cb)


PUA = re.compile(r'[\ue000-\uf8ff]')
PUA_N = [0]


def fix_pua(s):
    """PUA（外字）无法在无字体的情况下定值 ⇒ 按规范写 `〔未解析〕`（禁 `〓`、禁猜）。"""
    m = PUA.findall(s)
    if m:
        PUA_N[0] += len(m)
        s = PUA.sub('〔未解析〕', s)
    return s


def text_of(res):
    """RESOURCE → [(kind, text)]。"""
    c = list(res)
    types = [x.get('type') for x in c]
    if len(c) < 3 or types[0] != 'INT' or types[1] != 'GSCRIPT':
        return []
    if types == ['INT', 'GSCRIPT', 'STR', 'INT', 'INT', 'STR'] or \
       types == ['INT', 'GSCRIPT', 'STR', 'INT', 'INT'] or \
       types == ['INT', 'GSCRIPT', 'STR', 'INT', 'INT', 'STR', 'STR']:
        t = fix_pua((c[2].text or '').strip())
        return [('text', t)] if t else []
    # 选项：INT ＋ N×(GSCRIPT, STR)
    i = 1
    out = []
    while i + 1 < len(c):
        if c[i].get('type') == 'GSCRIPT' and c[i + 1].get('type') == 'STR':
            t = fix_pua((c[i + 1].text or '').strip())
            if t:
                out.append(('option', t))
            i += 2
        else:
            i += 1
    return out


def scene_key(name):
    m = re.match(r'^S(\d+)', name)
    if m:
        return (0, int(m.group(1)), name)
    if name.upper().startswith('SIKEN'):
        return (1, 0, name)
    if name.upper().startswith('START'):
        return (2, 0, name)
    if name.upper().startswith('END'):
        return (3, 0, name)
    return (4, 0, name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dir')
    ap.add_argument('out')
    ap.add_argument('--order')
    ap.add_argument('--stat', action='store_true')
    a = ap.parse_args()

    seen, files = set(), []
    for f in glob.glob(os.path.join(a.dir, '*')):        # ⚠ Windows 不区分大小写：*.XML/*.xml 会重复列出
        low = f.lower()
        if low.endswith('.xml') and low not in seen:
            seen.add(low); files.append(f)
    files.sort()
    names = [os.path.basename(f) for f in files]
    if a.order:
        want = [x.strip() for x in a.order.split(',') if x.strip()]
        files = sorted(files, key=lambda f: (want.index(os.path.basename(f).split('.')[0])
                                             if os.path.basename(f).split('.')[0] in want else 99,
                                             os.path.basename(f)))
    else:
        files = sorted(files, key=lambda f: scene_key(os.path.basename(f).split('.')[0]))

    lines, st = [], {'text': 0, 'option': 0, 'select': 0, 'file': 0, 'skip': 0}
    for p in files:
        try:
            root = ET.fromstring(open(p, 'rb').read().decode('utf-8'))
        except Exception as e:
            print('  [skip] %s: %s' % (os.path.basename(p), e)); st['skip'] += 1; continue
        got = []

        def cb(el, nxt):
            if el.tag != 'RESOURCE' or nxt is None or nxt.tag != 'FUNCTION':
                return
            fn = nxt.get('name')
            if fn == 'MESSAGE':
                for k, t in text_of(el):
                    if k == 'text':
                        got.append(t); st['text'] += 1
            elif fn == 'SELECT':
                st['select'] += 1
                for k, t in text_of(el):
                    if k == 'option':
                        got.append(t); st['option'] += 1

        walk(root, cb)
        st['file'] += 1
        lines.extend(got)

    with io.open(a.out, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(lines) + '\n')
    if a.stat:
        print('文件 %d（跳过 %d）／正文 %d ＋ 选项 %d（SELECT %d 组）＝ %d 行 / %d 字；PUA→〔未解析〕 %d 处'
              % (st['file'], st['skip'], st['text'], st['option'], st['select'],
                 len(lines), sum(len(x) for x in lines), PUA_N[0]))


if __name__ == '__main__':
    main()
