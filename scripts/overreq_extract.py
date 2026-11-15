#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[NS-JP]OVER REQUIEMZ —— 全文本提取（Unity + Otomate 命令式脚本 DSL）。

【2026-10-28 实证结构】
容器：XCZ→XCI→NCA(keygen18)→RomFS→Data/StreamingAssets/switch/script（UnityFS AssetBundle）
bundle 内 = 101 个 TextAsset（名字 OZ_00_00 … OZ_09_09），UTF-8 明文脚本（CRLF）
剧本语言（自定义 DSL，`function xxx()\n{ ... }`）：
  Message_CL( <layer> <msgid> <face> [# … #] )     ← 主文本（25,444 有效）
  SelectMessage_CL( … [# … #] )                      ← 选择前提问（220）
  Message( … [# … #] )                               ← 旧格式/包裹（块内多为脚本代码或被 // 注释）
  块内：**第一行 = 名札**（`null` ⇒ 无名札），其余行 = 框内换行 ⇒ 合并成一行
  选项：GoSelect2("A" "B" "label") / GoSelect3("A" "B" "C" "label" 0) / GoSPSelect3("A" "B" "C" [1 0 0] "label" 0)
主角：`@PlayerName@` → ユヒル（define 里 `variable PlayerName ( "ユヒル" )`）
排除：OZ_00_00（测试脚本：テスト/一括表示/エフェクトサンプル）、OZ_09_09（立ち絵レイヤーテスト）

用法: python scripts/overreq_extract.py [--out 提取结果/x.txt]
"""
import argparse
import os
import re
import sys

import UnityPy

BUNDLE = '_w_rq/sa/script'
HERO = 'ユヒル'
SKIP_ASSET = {'OZ_00_00', 'OZ_09_09', 'OZ_05_01_Z'}   # 测试脚本 ×2 + 未被引用的旧稿 Z 版

RE_MSG = re.compile(r'(?<![_A-Za-z0-9])(Message_CL|SelectMessage_CL|Message2|Message)'
                    r'(\s*\(\s*(?:[^()\[\]]|\[(?!\#))*?)\[#(.*?)#\]\s*\)', re.S)
RE_SEL = re.compile(r'(GoSelect\d|GoSPSelect\d)(\s*\(([^)]*)\))')
RE_QUOTED = re.compile(r'"([^"]*)"')
RE_COLOR = re.compile(r'<color(?:=[^>]*)?>|</color>')
RE_BR = re.compile(r'<br\s*/?>')
RE_CODE = re.compile(r'[()"]')
RE_RESNAME = re.compile(r'^[^\s]{1,24}\d{2}$')


def load_assets():
    env = UnityPy.load(BUNDLE)
    out = {}
    for o in env.objects:
        if str(o.type) != '49':
            continue
        d = o.read()
        nm = getattr(d, 'm_Name', '')
        raw = d.m_Script
        if isinstance(raw, str):
            raw = raw.encode('utf-8', 'surrogateescape')
        out[nm] = raw.decode('utf-8-sig')
    return out


def clean_line(s):
    s = RE_COLOR.sub('', s)
    s = RE_BR.sub('', s)
    s = s.replace('@PlayerName@', HERO)
    return s.strip().lstrip('　')


def _is_commented(text, pos):
    """命令本身是否被 `//` 注释掉（行首到命令起点之间出现 `//`）。"""
    bol = text.rfind('\n', 0, pos) + 1
    return '//' in text[bol:pos]


def parse(text, stats):
    """返回 [(pos, kind, text)]，kind = 'line' / 'opt'。"""
    ev = []
    for m in RE_MSG.finditer(text):
        if _is_commented(text, m.start()):
            stats['cmd_commented'] += 1
            continue
        body = m.group(3)
        lines = [l.strip() for l in body.replace('\r\n', '\n').split('\n')]
        lines = [l for l in lines if l and not l.startswith('//')]
        if not lines:
            stats['msg_skip_comment'] += 1
            continue
        head = lines[0]
        rest = lines[1:]
        if head != 'null':
            stats['name_drop'] += 1
        if not rest:
            stats['msg_no_body'] += 1
            continue
        # 脚本代码块（OZ_05_01_Z 用 Message 包命令）⇒ 不是台词
        if any(RE_CODE.search(x) for x in rest):
            stats['msg_code'] += 1
            continue
        s = ''.join(clean_line(x) for x in rest)
        if not s:
            continue
        # 教程块里的「立绘名」（`ドロシー` + `ドロシー01`）：正文是资源名，不是台词
        if RE_RESNAME.match(s) and s.startswith(head):
            stats['resname'] += 1
            continue
        ev.append((m.start(), 'line', s))
    for m in RE_SEL.finditer(text):
        if _is_commented(text, m.start()):
            stats['cmd_commented'] += 1
            continue
        args = RE_QUOTED.findall(m.group(3))
        if not args:
            continue
        n = int(re.search(r'\d', m.group(1)).group())
        for a in args[:n]:
            s = clean_line(a)
            if s and s not in ('null',):
                ev.append((m.start(), 'opt', s))
        stats['opt_groups'] += 1
    ev.sort(key=lambda x: x[0])
    return ev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out')
    ap.add_argument('--dump', action='store_true')
    a = ap.parse_args()
    assets = load_assets()
    print('[i] assets', len(assets))
    stats = {k: 0 for k in ('msg_skip_comment', 'name_drop', 'msg_no_body', 'msg_code', 'opt_groups', 'dup', 'cmd_commented', 'resname')}
    lines = []
    for nm in sorted(assets):
        if nm in SKIP_ASSET:
            print('[i] skip asset', nm)
            continue
        ev = parse(assets[nm], stats)
        n0 = len(lines)
        for pos, kind, s in ev:
            lines.append(s)
        if a.dump:
            print('  %-24s %5d 条  (%d 行)' % (nm, len(ev), len(lines) - n0))
    # 相邻完全重复（if/else 互斥分支各排一份）
    out = []
    for x in lines:
        if out and out[-1] == x:
            stats['dup'] += 1
            continue
        out.append(x)
    print('[i] stats', stats)
    print('[i] lines', len(out), 'chars', sum(len(x) for x in out))
    for x in sorted(out, key=len)[-3:]:
        print('[max] %d %s' % (len(x), x[:80]))
    if a.out:
        with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write('\n'.join(out) + '\n')
        print('[ok]', a.out)


if __name__ == '__main__':
    main()
