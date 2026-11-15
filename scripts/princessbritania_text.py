#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[PC-JP]Princess Britania～ミューズの宝剣～（KiriKiri XP3 ＋ Crafter/RAT 扩展 KAG3 · linemode=free）全文本提取。

L0 判据（system/LineMode.tjs 注释 L117-126 ＋ parseR/emptyCheck 实现，引擎代码级）：
  linemode=free ⇒ 空行 → [p]（页断/一次点击）；连续非空行 → [r]（软换行，同框）。
  ⇒ 一个 text box = 连续“有正文字符”的脚本行构成的一段；空行/纯指令行/纯名字行都断框。
  【名】 出现在行首 ⇒ 独立名字窗（onDispname / parseDispname）→ 剔（不进正文）。
  [A_名_N ...]      ⇒ 语音触发（entryNextVoice），不产字 → 剔。
  [＠名] / [＠名前切替] ⇒ 主角名宏（emb exp=f.name）→ 内联保留，按游戏内默认名解析为「クロエ」。
  其余 [tag ...]    ⇒ 表情/立绘/SE/BGM/过渡/msgoff 等控制标签 → 剔。
  [seladd text="X"] ⇒ 选项（一行一条）；[select]/[endselect] 无正文 → 剔。
  [msgoff]/[msgon]  ⇒ 本作无 [msgon]，[msgoff] 仅过渡期隐藏消息层、随下次绘制自动恢复 → 忽略。

双版判定：用户规则「一框多次点击 / 一次点击多框⇒出双版」。本作文本框均为一次点击一框，
  无脚本级一次点击多框（无 [l]/[p]/[nowait] 多 message layer 现象），故**判定为单版**，一行一框交付。

输出：每个 text box 一行（框内连续脚本行合并为一行，无内嵌换行，符合“一行=一个文本框”）；
  选项按源码顺序与正交叉错输出（一行一条）。UTF-8 BOM / 纯 LF。

用法：
  python scripts/princessbritania_text.py <scenario_dir> <out_txt>
  （scenario_dir 即解包后的 xp3data/scenario，内含 *.ks）
"""
import sys, os, re, glob, argparse

EXCLUDE = {'macro.ks', 'parsermacro.ks', 'gototitle.ks', 'start.ks'}


def read_ks(p):
    b = open(p, 'rb').read()
    if b[:2] == b'\xff\xfe':
        return b.decode('utf-16')
    if b[:3] == b'\xef\xbb\xbf':
        return b.decode('utf-8-sig')
    if b.count(0) > len(b) * 0.25:
        return b.decode('utf-16-le', 'replace')
    return b.decode('cp932', 'replace')


TAG_RE = re.compile(r'\[([^\[\]]*)\]')
NAME_HEAD_RE = re.compile(r'^【[^】]*】')


def line_text(s):
    """剥离所有非正文标签，内联展开 [＠名]→クロエ；返回该行正文（可能为空）。"""
    out = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == '[':
            j = s.find(']', i)
            if j < 0:
                out.append(s[i:]); break
            inner = s[i+1:j]
            m = re.match(r'([^\[\]\s=]+)', inner)
            name = m.group(1) if m else ''
            if name.startswith('＠'):
                out.append('クロエ')          # 主角名宏 → 内联
            # 其余标签（含 A_ 语音、表情、立绘、SE、msgoff 等）一律丢弃
            i = j + 1
            continue
        out.append(c)
        i += 1
    t = ''.join(out).strip()
    return t


def strip_name(t):
    """行首 【名】 是独立名字窗 → 去掉；其余字面保留。"""
    m = NAME_HEAD_RE.match(t)
    if m:
        t = t[m.end():].strip()
    return t


def extract_file(path):
    """返回 (out_lines, n_boxes, n_opts)，out_lines 按源码顺序：
       - 每个 text box → 一行（框内连续脚本行已合并）
       - 每个选项 → 一行（按出现顺序，与剧本位置一致）
    """
    t = read_ks(path)
    out = []
    n_boxes = 0
    n_opts = 0
    cur = []
    for raw in t.split('\n'):
        s = raw.strip()
        if not s:                       # 空行 → 断框
            if cur: out.append(''.join(cur)); n_boxes += 1; cur = []
            continue
        if s.startswith('*') or s.startswith(';'):
            if cur: out.append(''.join(cur)); n_boxes += 1; cur = []
            continue
        if s.startswith('[seladd'):
            if cur: out.append(''.join(cur)); n_boxes += 1; cur = []
            tm = re.search(r'text="([^"]*)"', s)
            if tm:
                out.append(tm.group(1))   # 选项一行一条，位置随源码
                n_opts += 1
            continue
        if s.startswith('[select') or s.startswith('[endselect'):
            continue
        # 普通文本行
        line = strip_name(line_text(s))
        if not line:                    # 纯指令/纯名字行 → 断框（不贡献正文）
            if cur: out.append(''.join(cur)); n_boxes += 1; cur = []
            continue
        # 纯 ASCII 行（无任何非 ASCII 字符）＝非台词残留/笔误（如 `[expr]s`）→ 剔
        if not any(ord(c) > 127 for c in line):
            if cur: out.append(''.join(cur)); n_boxes += 1; cur = []
            continue
        cur.append(line)
    if cur:
        out.append(''.join(cur)); n_boxes += 1
    return out, n_boxes, n_opts


def main():
    ap = argparse.ArgumentParser(description="[PC-JP]Princess Britania text extractor (KiriKiri+Crafter/RAT, linemode=free)")
    ap.add_argument("scenario_dir", help="解包后的 scenario 目录（含 *.ks）")
    ap.add_argument("out", help="输出 txt（UTF-8 BOM / LF）")
    args = ap.parse_args()

    files = sorted(f for f in glob.glob(os.path.join(args.scenario_dir, '*.ks'))
                  if 'replay' not in f and os.path.basename(f) not in EXCLUDE)
    out_lines = []
    stats = dict(files=0, boxes=0, opts=0)
    for f in files:
        lines, nb, no = extract_file(f)
        stats['files'] += 1
        stats['boxes'] += nb
        stats['opts'] += no
        out_lines.extend(lines)
    stats['total_lines'] = len(out_lines)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, 'w', encoding='utf-8-sig', newline='\n') as fh:
        for ln in out_lines:
            fh.write(ln + '\n')
    print(stats, '->', os.path.abspath(args.out))
    return stats


if __name__ == '__main__':
    main()
