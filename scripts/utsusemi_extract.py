# -*- coding: utf-8 -*-
"""空蝉の廻 (NS-JP) 文本提取

引擎：Unity IL2CPP + 自研纯文本 DSL（scenario.unity3d 内 915 个 TextAsset）
记录形状（一次点击＝一框＝一行）：
  @talk [voice=..] [name=..]      ← 开框
  <正文行>（\r\n 软换行 ⇒ 合并）   ← 框内可插 @talkov（仅换表情立绘）
  @hitret                          ← 一次点击（推进/等待）
选项：@choice text=<文本> file=<跳转目标> … @choiceEnd
  ⇒ 追加一次点击；@talkov 在框内出现（同一框的表情切换），不切框。
"""
import collections
import glob
import os
import re
import sys

import UnityPy

B = '_work_utsusemi/romfs/Data/StreamingAssets/assets/resources/scenario/scenario.unity3d'
OUT = '提取结果/[NS-JP]空蝉の廻.txt'
NAME = '天音'
SKIP = re.compile(r'^(um_tDebug|exp_check|bundle_test|test_sound|voice_test|'
                  r'macro_|white_flash|red_flash|bunki_test|ov|Recollection|Start)')
# 框内允许出现、且不切框的指令
MIDBOX = ('@talkov',)


def load():
    env = UnityPy.load(B)
    d = {}
    for o in env.objects:
        if o.type.name != 'TextAsset':
            continue
        ta = o.read()
        d[ta.m_Name] = str(ta.m_Script).replace('\ufeff', '').replace('\r\n', '\n')
    return d


def natural(n):
    return [int(x) if x.isdigit() else x for x in re.split(r'(\d+)', n)]


def clean(s):
    s = s.replace('<pf>', NAME).replace('[r]', '')
    return s.strip()


def parse(t):
    """→ (lines, stat)。一次点击一行：@talk…@hitret；@choice 一条一行。"""
    lines = []
    stat = collections.Counter()
    body = []
    in_box = False
    for raw in t.split('\n'):
        s = raw.strip()
        if not s or s.startswith(';') or s.startswith('*'):
            stat['skip'] += 1
            continue
        if s.startswith('@'):
            cmd = s.split(' ', 1)[0].split('\t', 1)[0]
            if cmd == '@talk':
                if in_box:
                    stat['talk_before_hitret'] += 1
                    _flush(body, lines, stat)
                body = []
                in_box = True
            elif cmd == '@hitret':
                if in_box:
                    _flush(body, lines, stat)
                    body = []
                    in_box = False
                else:
                    stat['orphan_hitret'] += 1
            elif cmd == '@choice':
                m = re.match(r'@choice\s+text=(.*?)(?:\s+file=|$)', s)
                if m:
                    o = clean(m.group(1))
                    if o:
                        lines.append(o)
                        stat['opt'] += 1
                else:
                    stat['choice_notext'] += 1
            elif cmd in MIDBOX:
                stat['midbox_' + cmd] += 1
                continue
            else:
                if in_box:
                    stat['cmd_in_box_' + cmd] += 1
                in_box = False
                body = []
            continue
        if in_box:
            # `;` 注释行、`>um_t01_75` 型作者注（脚本残留，非上屏文本）一律不入正文
            if not s.startswith(';') and not s.startswith('>'):
                body.append(raw)
    if in_box:
        stat['unclosed'] += 1
    return lines, stat


def _flush(body, lines, stat):
    txt = clean(''.join(x.strip() for x in body))
    if txt:
        lines.append(txt)
        stat['box'] += 1
    else:
        stat['empty_box'] += 1


def main():
    d = load()
    names = sorted([n for n in d if not SKIP.match(n)], key=natural)
    print('files used', len(names), 'skipped', len(d) - len(names))
    tot = collections.Counter()
    out = []
    for n in names:
        ls, st = parse(d[n])
        tot += st
        out.extend(ls)
    print('lines', len(out))
    print(dict(tot))
    body = '\n'.join(out) + '\n'
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'wb').write(b'\xef\xbb\xbf' + body.encode('utf-8'))
    print('wrote', OUT, len(body))


if __name__ == '__main__':
    main()
