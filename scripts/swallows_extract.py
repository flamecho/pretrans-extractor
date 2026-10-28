#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""My9Swallows TOPSTARS LEAGUE —— Unity + 纯文本脚本（与 Honey Vibes 同引擎）。

链路：XCI → secure HFS0(4 NCA) → Program NCA(Standard crypto, keygen 18) →
      romfs `Data/StreamingAssets/Script/*.h`(UTF-8) + `Setting/*.csv`

记录（L1 命令自定界）：
    SET_TALK( 角色ID, WIN|SNS, "显示名", 语音ID, "正文" )   ← 一次点击 = 一行
    `\` = 框内软换行 ⇒ 删除合并；其后跟全角空格（缩进）一并删
    CHOICE_JUMP( <番号>, ... ) ⇒ 该点弹选项，文本在 CHOICE.csv「選択肢」列
"""
import csv, os, re, sys

SETT = '_w_W1_swallows/out'
OUT = '提取结果/[NS-JP]My9Swallows TOPSTARS LEAGUE.txt'
PROTAG = '%+&'
TALK = re.compile(r'SET_TALK\s*\(\s*([^,]+?)\s*,\s*([^,]+?)\s*,\s*"((?:[^"\\]|\\.)*)"\s*,'
                  r'\s*([^,]+?)\s*,\s*"((?:[^"\\]|\\.)*)"\s*\)')
CHOICE_JUMP = re.compile(r'CHOICE_JUMP\s*\(\s*([^,)]+?)\s*,')


def unescape(s):
    return s.replace('\\\u3000', '').replace('\\', '')


def read_csv(p):
    with open(p, encoding='utf-8-sig', newline='') as f:
        return list(csv.reader(f))


def load_choices():
    rows = read_csv(os.path.join(SETT, 'CHOICE.csv'))
    out, cur = {}, None
    for r in rows[1:]:
        if len(r) < 4:
            continue
        if r[0].strip():
            cur = r[0].strip()
            out.setdefault(cur, [])
        if cur is None:
            continue
        o = r[3].strip()
        if o:
            out[cur].append(unescape(o))
    return out


def load_dict(fn):
    out = []
    p = os.path.join(SETT, fn)
    if not os.path.exists(p):
        return out
    for r in read_csv(p)[1:]:
        if len(r) < 4:
            continue
        w, c = r[2].strip(), r[3].strip()
        if w and c:
            out.append((w, re.sub(r'\s*\n\s*', '', c)))
    return out


def main():
    order = []
    for r in read_csv(os.path.join(SETT, 'STORYFLOW.csv'))[1:]:
        if len(r) > 2 and r[2].strip():
            order.append(r[2].strip())
    have = {os.path.splitext(f)[0] for f in os.listdir(SETT) if f.endswith('.h')}
    seq = [x for x in order if x in have]
    extra = sorted(have - set(order))
    choices = load_choices()
    lines, emitted, n_talk, n_opt = [], set(), 0, 0
    for name in seq:
        text = open(os.path.join(SETT, name + '.h'), encoding='utf-8', errors='replace').read()
        for ln in text.splitlines():
            m = TALK.search(ln)
            if m:
                t = unescape(m.group(5)).strip()
                if t:
                    lines.append(t)
                    n_talk += 1
                continue
            m = CHOICE_JUMP.search(ln)
            if m:
                cid = m.group(1).strip()
                if cid in choices and cid not in emitted:
                    for o in choices[cid]:
                        lines.append(o)
                        n_opt += 1
                    emitted.add(cid)
    nd = 0
    for fn in ('DICT.csv', 'DICT_BASEBALL.csv'):
        for w, c in load_dict(fn):
            lines.append(f'【{w}】{c}')
            nd += 1
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('脚本 %d/%d（磁盘 %d，未列 flow %d）' % (len(seq), len(order), len(have), len(extra)))
    print('正文 %d / 选项 %d（%d 组，表内 %d 组）/ 辞典 %d' % (n_talk, n_opt, len(emitted), len(choices), nd))
    print('合计 %d 行 -> %s' % (len(lines), OUT))
    if extra:
        print('未列入 STORYFLOW:', extra[:8])
    unused = [k for k in choices if k not in emitted]
    if unused:
        print('⚠ 未引用的选项组 %d: %s' % (len(unused), unused[:5]))


if __name__ == '__main__':
    main()
