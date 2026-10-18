#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest.py —— `check_text.py` 判据的回归测试（改判据前后各跑一次）。

为什么有它：品检的每一条判据都是「历史上被退回来过的问题」的沉淀，但**改判据没有东西拦得住回退**。
本脚本把那些返工点固化成 20 个微型样本，每条断言「该报的报了、不该报的没报」。

用法:
  python scripts/selftest.py            # 全跑，退出码 0 = 全通过
  python scripts/selftest.py -v         # 额外打印每个样本的实际 [E]/[W]
  python scripts/selftest.py 半角假名    # 只跑名字含该子串的用例

新增判据时：**先加一条 case 到 CASES**，再改 check_text.py。
"""
import argparse
import contextlib
import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_text import check          # noqa: E402

BOM = b'\xef\xbb\xbf'
CLEAN = 'きょうはいい天気ですね。\n「そうですね。」\n'


def case(name, text, e=(), w=(), not_e=(), names=(), bom=True, nl='\n', note=''):
    """构造一个样本：text 按 nl 连接行；e/w/not_e 是对 [E]/[W] 消息的子串断言。"""
    body = text.replace('\n', nl)
    return dict(name=name, data=(BOM if bom else b'') + body.encode('utf-8'),
                e=list(e), w=list(w), not_e=list(not_e), names=list(names), note=note)


CASES = [
    # ── 基线 ──────────────────────────────────────────────
    case('干净样本', CLEAN,
         note='规范产物不应有任何 E/W'),
    case('无 BOM', CLEAN, e=['BOM 缺失'], bom=False),
    case('CRLF', CLEAN, e=['出现 CR'], nl='\r\n'),

    # ── 形态层 ────────────────────────────────────────────
    case('半角假名', 'これはｱｲｳです。\n', e=['半角假名'],
         note='最高频漏检之一：cp932 首字节损坏'),
    case('半角标点', 'テスト｡です。\n', w=['半角标点'], e=[],
         note='U+FF61-65 是原文用字，只能 W'),
    case('私用区PUA', 'テスト\uE000です。\n', e=['私用区 PUA']),
    case('解码失败', 'テスト\ufffdです。\n', e=['U+FFFD']),
    case('占位符〓', 'テスト\u3013です。\n', e=['`\u3013` 占位符']),
    case('控制符', 'テスト\x01です。\n', e=['控制符(C0)']),

    # ── 引号 / 行首 ───────────────────────────────────────
    case('引号不配对', 'これは「テストです。\n', e=['引号不配对'],
         note='第二高频漏检'),
    case('行首孤立标点', '、これはテストです。\n', e=['行首孤立标点']),
    case('颜文字单侧括号', 'テスト（￣Д￣；です。\n', not_e=['引号不配对'],
         note='颜文本就单侧括号，不得误报'),

    # ── 说话人残留 ────────────────────────────────────────
    case('独立名札行', '【秀雄】\n【秀雄】\n', e=['独立名字札行']),
    case('行首【名】+正文', '【秀雄】「おはよう」\n【秀雄】「おはよう」\n',
         e=['行首【名】＋正文']),
    case('行首名前冒号', '秀雄：おはよう\n秀雄：おはよう\n', e=['行首「名前：」']),
    case('字段标签放行', '送信者：室田要\n送信者：室田要\n', not_e=['行首「名前：」'],
         note='邮件表/书信的字段名是正文'),
    case('特效括号放行', '【カラダ……】\n【カラダ……】\n', not_e=['独立名字札行'],
         note='含句读的【】是上屏特效，非名札'),

    # ── 内容层 ────────────────────────────────────────────
    case('句号缺失', 'テスト、ああ\n' * 320, e=['全篇 0 个句号'],
         note='cp932 0x8140 槽被当全角空格清洗'),
    case('插入宏残留', 'テスト@GameLastです。\n', e=['未解析插入宏']),
    case('主角名缺失', CLEAN, w=['主角名'], names=['アリス']),
    case('主角名命中', CLEAN + '由奈はここにいる。\n', not_e=[], w=[], names=['由奈']),
]


def split_msgs(out):
    e = [l[6:] for l in out.split('\n') if l.startswith('  [E] ')]
    w = [l[6:] for l in out.split('\n') if l.startswith('  [W] ')]
    return e, w


def run(c, verbose):
    fd, p = tempfile.mkstemp(suffix='.txt')
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(c['data'])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            check(p, c['names'], 200.0, True)
        out = buf.getvalue()
    finally:
        if os.path.exists(p):
            os.remove(p)
    E, W = split_msgs(out)
    bad = []
    for s in c['e']:
        if not any(s in x for x in E):
            bad.append('应有 [E] %r' % s)
    for s in c['w']:
        if not any(s in x for x in W):
            bad.append('应有 [W] %r' % s)
    for s in c['not_e']:
        if any(s in x for x in E):
            bad.append('不应有 [E] %r' % s)
    if verbose or bad:
        print('  %s [E] %s' % (c['name'], E or '—'))
        print('  %s [W] %s' % (c['name'], W or '—'))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-v', '--verbose', action='store_true')
    ap.add_argument('filter', nargs='?', default='')
    a = ap.parse_args()
    picked = [c for c in CASES if a.filter in c['name']]
    if not picked:
        sys.exit('没有匹配 %r 的用例' % a.filter)
    fails = 0
    for c in picked:
        bad = run(c, a.verbose)
        mark = 'FAIL' if bad else ' ok '
        print('[%s] %s%s' % (mark, c['name'], ('  ← ' + c['note']) if c['note'] and bad else ''))
        for b in bad:
            print('       %s' % b)
        fails += 1 if bad else 0
    print('\n--- 用例 %d ｜ 通过 %d ｜ 失败 %d ---'
          % (len(picked), len(picked) - fails, fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
