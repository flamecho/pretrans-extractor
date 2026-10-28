#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""colorful_bunka_extract.py —— 放課後colorful＊step～ぶんかぶ！～（PSP）全文本提取。

链路：ISO9660 -> PSP_GAME/USRDIR/DATA/SCRIPT.cpk (CRI CPK) -> *.ks (cp932 明文 DSL)
DSL：
  [message voice=".." nametxt=".."]  ……  [/message]   ＝ 1 次点击（名札在独立名字窗）
  [BR]                                               ＝ 框内软换行（≤3 行/框，无清框指令）
  [SELECT WORD=".." FILE=".."]                        ＝ 选项（一行一条）
其余 [BGIMAGE]/[BGM]/[SE]/[cg]/[CHARA*]/[LOVE]/[STOP]/[NEXT]/[MOVIE]/[ROUTE_*] 无正文。

用法：
  python scripts/colorful_bunka_extract.py --script _work_colorful_bunka/script \
      --out "提取结果/[PSP-JP]放課後colorful＊step～ぶんかぶ！～.txt"
"""
import argparse
import os
import re
import sys

FAMILY = '小日向'
FIRST = 'ハルコ'

MSG_RE = re.compile(r'^\[message\b')
NAME_RE = re.compile(r'nametxt\s*=\s*"([^"]*)"')
SEL_RE = re.compile(r'^\[SELECT\b.*?WORD\s*=\s*"([^"]*)"')
MACROS = {'[FIRSTNAME]': FIRST, '[FAMILYNAME]': FAMILY, '[STAYNAME]': ''}


def sorting(fn):
    """按剧本流程排序：共通/演劇部线 -> 吹奏楽部线 -> 角色部活 -> おまけ。"""
    base = fn[:-3] if fn.endswith('.ks') else fn
    if base.startswith('s_bunkabu'):      # 练习/系统提示（STATUS_SE）
        return None
    if base.startswith('bunkabu_omake'):
        cls = 3
    elif base.startswith('bunkabu_0_021_0_1'):
        cls = 1          # 選擇肢「吹奏楽部」→ 吹奏楽部線の先頭
    elif base.startswith('bunkabu_0'):
        cls = 0
    elif base.startswith('bunkabu_1'):
        cls = 1
    else:
        cls = 2
    nums = tuple(int(x) for x in re.findall(r'\d+', base))
    return (cls, base.split('_')[0] if cls == 2 else '', nums, base)


def clean(body_lines):
    """合并框内软换行，去掉续行缩进（全角空格），剥除宏。"""
    parts = []
    for i, ln in enumerate(body_lines):
        s = ln
        if s.startswith(';'):          # 误写进正文框的注释
            continue
        if s.strip() == '[BR]':
            continue
        if s.endswith('[BR]'):
            s = s[:-4]
        elif '[BR]' in s:
            s = s.replace('[BR]', '')
        if i:                          # 续行：去行首缩进
            s = s.lstrip('\u3000 \t')
        else:
            s = s.lstrip('\u3000 \t')
        if not s.strip():
            continue
        parts.append(s.rstrip())
    line = ''.join(parts)
    for k, v in MACROS.items():
        line = line.replace(k, v)
    line = re.sub(r'\[[A-Za-z0-9_]+[^\]]*\]', '', line)
    line = line.strip('\u3000 \t')
    line = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', line)
    return line


def parse_file(path):
    raw = open(path, 'rb').read().decode('cp932', 'replace')
    out = []
    cur = None
    for ln in raw.split('\r\n'):
        if MSG_RE.match(ln):
            if cur is not None:
                out.append(('msg', cur))
            cur = []
            rest = ln.split(']', 1)[1] if ']' in ln else ''
            if rest.strip():
                cur.append(rest)
            continue
        if ln.startswith('[/message]'):
            if cur is not None:
                out.append(('msg', cur))
                cur = None
            continue
        m = SEL_RE.match(ln)
        if m:
            if cur is not None:
                out.append(('msg', cur))
                cur = None
            out.append(('opt', m.group(1)))
            continue
        if cur is not None:
            cur.append(ln)
    if cur is not None:
        out.append(('msg', cur))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--script', default='_work_colorful_bunka/script')
    ap.add_argument('--out', required=True)
    ap.add_argument('--stats', action='store_true')
    a = ap.parse_args()

    files = sorted((f for f in os.listdir(a.script) if f.endswith('.ks')),
                   key=lambda f: (sorting(f) is None, sorting(f) or ()))
    lines, nmsg, nopt, skipped = [], 0, 0, []
    for fn in files:
        key = sorting(fn)
        if key is None:
            skipped.append(fn)
            continue
        for kind, val in parse_file(os.path.join(a.script, fn)):
            if kind == 'opt':
                t = val.strip()
                if t:
                    lines.append(t)
                    nopt += 1
            else:
                t = clean(val)
                if t:
                    lines.append(t)
                    nmsg += 1

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(('\n'.join(lines) + '\n').encode('utf-8'))
    if a.stats:
        print('files=%d  msg=%d  opt=%d  total=%d  skipped=%d'
              % (len(files) - len(skipped), nmsg, nopt, len(lines), len(skipped)))
        print('skipped:', skipped)
        print('chars:', sum(len(x) for x in lines))


if __name__ == '__main__':
    sys.exit(main())
