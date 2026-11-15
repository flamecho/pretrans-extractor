#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""神々の悪戯 Unite Edition（NS）→ 全文本

链路：NSP → Program NCA → RomFS → `Data/StreamingAssets/scenario/scenario00|01`（UnityFS 包，Unity 2019.4.26f1）
      包内 **每个 TextAsset = 一个剧本文件**（UTF-8 明文，自制 KAG 风语法）

语法（实测）：
    ;//...                     注释（含工具写的 `;//[テキスト]//` 占位）
    [bg …] [wait …] [anim …]   指令行（整行 `[...]`）
    [アポロン voice="5100" …]  立绘/语音指令（整行，名字在方括号里 ⇒ 不是正文）
    [seladd text="手を繋ぐ" target=*label]   选项
    *label|                    标签
    【アポロン・アガナ・べレア】              名字窗（独立一行）⇒ 丢弃
    其余非空行                  正文（台词「…」/ 地の文）

★ 一行＝一次点击？**不是**：同一框的多行是**排版折行**，靠空行分框：
     `自分たちの力では到底ゼウスには敵わないと、` ＋ `私は誰かを呼びに行こうと決めた。`（无空行）= 1 框
  判据：组内首行可能以 `、` 结尾（明显未完结）而末行收尾 ⇒ 只能同框。
  `（` 缩进 `　` 出现在续行（`　『寒い』で片付けられたよォ～`）＝折行痕迹。

★ 名札 `【…】` 单独占行且紧贴台词 ⇒ 独立名字窗 ⇒ 整行丢弃（`【草薙　結衣/player】` 里的
  `/player` 表示「此处显示玩家输入名」，默认 草薙　結衣；正文里他人称她「結衣」为字面原文）。

用法：
    python scripts/kamigami_scr_extract.py <scenario00> [scenario01 ...] --out out.txt
"""
import os
import re
import sys

TAG_LINE = re.compile(r'^\s*\[[^\]]*\]\s*$')
SELADD = re.compile(r'^\s*\[seladd\b([^\]]*)\]\s*$')
TEXT_ATTR = re.compile(r'text="([^"]*)"')
NAME_LINE = re.compile(r'^【[^】]{1,40}】$')
CMD_LINE = re.compile(r'^@[A-Za-z_]')      # `@varadd trust …` 这类脚本指令（不带方括号）

# 主人公名占位。默认值证据：global-metadata.dat 里 `結衣` `草薙` `ユイ` 三串相邻
# （名字窗写作 `【草薙　結衣/player】`，`/player` 表示此处显示玩家输入名）。
PLACEHOLDERS = (
    ('[主人公氏名]', '草薙　結衣'),
    ('[主人公苗字]', '草薙'),
    ('[主人公愛称]', 'ユイ'),
    ('[主人公]', '結衣'),
)


def iter_textassets(path):
    import UnityPy
    env = UnityPy.load(path)
    for o in env.objects:
        if o.type.name != 'TextAsset':
            continue
        d = o.read()
        raw = d.m_Script
        b = raw.encode('utf-8', 'surrogateescape') if isinstance(raw, str) else raw
        try:
            t = b.decode('utf-8')
        except UnicodeDecodeError:
            t = b.decode('cp932', 'replace')
        yield getattr(d, 'm_Name', ''), t


def boxes(text):
    """剧本文本 → 行列表（一框一行；选项单列）"""
    out = []
    buf = []

    def flush():
        if buf:
            s = ''.join(buf).strip()
            if s and s != 'スクリプト中で使用されていません。':
                out.append(s)
            buf.clear()

    for raw in text.split('\n'):
        s = raw.strip()
        if not s:
            flush()
            continue
        if s.startswith(';//'):
            continue
        m = SELADD.match(s)
        if m:
            flush()
            tm = TEXT_ATTR.search(m.group(1))
            if tm:
                out.append(tm.group(1).strip())
            continue
        if TAG_LINE.match(s) or s.startswith('*') or CMD_LINE.match(s):
            flush()
            continue
        if NAME_LINE.match(s):          # 名字窗：独立一行，丢
            continue
        buf.append(s)
    flush()
    res = []
    for x in out:
        for a, b in PLACEHOLDERS:
            x = x.replace(a, b)
        if x:
            res.append(x)
    return res


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out_path = 'out.txt'
    if '--out' in sys.argv:
        out_path = sys.argv[sys.argv.index('--out') + 1]
        args = [a for a in args if a != out_path]
    lines = []
    per = []
    for p in args:
        items = sorted(iter_textassets(p), key=lambda x: x[0])
        n = 0
        for name, t in items:
            got = boxes(t)
            lines.extend(got)
            n += len(got)
            per.append((os.path.basename(p), name, len(got)))
        print('%s: %d 个剧本，%d 行' % (os.path.basename(p), len(items), n))
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    with open(out_path, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(lines) + '\n')
    print('合计 %d 行' % len(lines))


if __name__ == '__main__':
    main()
