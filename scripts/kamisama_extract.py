#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""もし、この世界に神様がいるとするならば。 —— resources.assets 内 .kaiso 剧本 → 全文本。

记录（L1，行首命令自定界）：
    ＠話者名            ← 名字窗，每页一个（剔除）
    本文（可跨 2–3 行，续行以全角空格缩进）⇒ 合并
    <pb>                ← **换页**（清屏）⇒ 页边界
    <wait key="true">   ← **框内等待按键（不清屏）**⇒ 一次点击的段边界（2026-10-27 补）
    <wait time="NNNN">  ← 演出停顿，不换行，**不是**点击
    <select> … <case value="…">  ← 选项文本（一行一条）
    <其它 tag> / //注释  ← 演出、不取
    %name% / %family%   ← 主角名/姓 占位（回填 ハルカ / 来実）

版式：双版对照 —— 一页内 ≥2 次点击时，先列各「段行」（＝一次点击一行），再列「合并行」（＝整页一屏）。
"""
import os, re, sys

SRC = '_w_W1_kamisama/out/resources.assets'
OUT = '提取结果/[NS-JP]もし、この世界に神様がいるとするならば。.txt'
NAME = 'ハルカ'
FAMILY = '来実'
TAG = re.compile(r'<[^>]*>')
WAIT_KEY = re.compile(r'<wait\s+key')
CASE_VAL = re.compile(r'value\s*=\s*"([^"]*)"')   # 有 value="…" 与 value = "…" 两种写法


def decode(d):
    b = d.m_Script.encode('utf-8', 'surrogateescape')
    if b[:2] == b'\xff\xfe':
        b = b[2:]
    return b.decode('utf-16-le', 'replace')


def clean(s):
    s = TAG.sub('', s)
    s = s.replace('%name%', NAME).replace('%family%', FAMILY)
    return s.strip().strip('\u3000').strip()


def parse(t):
    """返回成品行序列（段行＋合并行＋选项）。"""
    out = []
    page = []          # 本页各段
    seg = []           # 当前段的正文行
    opts = None        # 正在收集的 <select> 选项

    def flush_seg():
        if seg:
            s = ''.join(seg)
            if s:
                page.append(s)
            seg.clear()

    def flush_page():
        flush_seg()
        if len(page) >= 2:                 # ≥2 次点击才出合并行
            out.extend(page)
            out.append(''.join(page))
        elif page:
            out.append(page[0])
        page.clear()

    for raw in t.replace('\r\n', '\n').split('\n'):
        s = raw.strip()
        if not s:
            continue
        if s.startswith('＠'):
            flush_page()
            continue
        if s.startswith('//'):
            continue
        if s.startswith('<'):
            if s.startswith('<pb'):
                flush_page()
                continue
            if WAIT_KEY.match(s):          # 框内等待按键 ⇒ 段边界
                flush_seg()
                continue
            if re.match(r'<select>', s) or re.match(r'<moshikami\s*>', s):
                # 两种选项容器：普通选项 <select>、神様選択肢 <moshikami>（<selectitem> 是另一个标签，别混）
                opts = []
                continue
            if opts is not None and s.startswith('<case'):
                m = CASE_VAL.search(s)
                if m:
                    v = clean(m.group(1))
                    if v:
                        opts.append(v)
                continue
            if re.match(r'</select>', s) or re.match(r'</moshikami\s*>', s):
                if opts:
                    flush_page()
                    out.extend(opts)
                opts = None
                continue
            continue                        # <wait time=…> 等演出指令
        seg.append(clean(raw))
    flush_page()
    return [x for x in out if x]


def main():
    import UnityPy
    env = UnityPy.load(SRC)
    files = []
    for o in env.objects:
        if o.type.name != 'TextAsset':
            continue
        d = o.read()
        if d.m_Name.endswith('.kaiso'):
            files.append((d.m_Name, decode(d)))
    files.sort()
    allout = []
    for nm, t in files:
        got = parse(t)
        allout.extend(got)
        print('%-26s %5d' % (nm, len(got)))
    out = sys.argv[1] if len(sys.argv) > 1 else OUT
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(allout) + '\n')
    print('文件 %d / 合计 %d 行 -> %s' % (len(files), len(allout), out))


if __name__ == '__main__':
    main()
