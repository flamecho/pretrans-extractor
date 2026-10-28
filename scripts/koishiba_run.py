#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""恋は校則に縛られない！（PSP）—— USRDIR/DATA/sc.cpk → 全文本。

命令集（≥0xFF00，本作实测）：
  FFF0 <style><NAME>   说话人名札（run 首码为样式符）→ 整段丢弃（§0 不加说话人前缀）
  FFFF <TEXT>          正文框开始（＝一次点击）；空 run 为占位框
  FFFE <TEXT>          同框内换行（合并，去行首全角空格）
  FFFB                 消息分隔
  FFFD                 框结束
  FFE6 / FFE7          主角 姓 / 名 占位（名札区内丢弃；正文内 inline 填默认名）
  其余 0xFFxx          语音 id / 坐标 / 图标等参数 → 丢弃

选项：与正文同流（连续 FFFF），每个选项自带首码 < 0x20 的 ID/装饰前缀，剥掉即得文本。

用法：python scripts/koishiba_run.py <sc.cpk> <out.txt>
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cpk import CPK  # noqa: E402
from koishiba_charset import (decode, NAME_SURNAME, NAME_GIVEN)  # noqa: E402

C_NAME, C_BOX, C_BR = 0xFFF0, 0xFFFF, 0xFFFE
C_SEP, C_END = 0xFFFB, 0xFFFD
C_SURNAME, C_GIVEN = 0xFFE6, 0xFFE7
# 同框内的另段文本（不同显示样式：咳き込み等の効果音テキスト）
TEXT_CMDS = {0xFF8F}


def toks(data):
    n = len(data) // 2
    vals = struct.unpack_from('<%dH' % n, data, 0)
    out = []
    cur, run = 0, []
    for v in vals:
        if v >= 0xFF00:
            out.append((cur, run))
            cur, run = v, []
        else:
            run.append(v)
    out.append((cur, run))
    return out


def strip_lead_codes(ws):
    i = 0
    while i < len(ws) and ws[i] < 0x20:
        i += 1
    return ws[i:]


def render(items):
    s = []
    first = True
    for kind, val in items:
        if kind == 'n':
            s.append(val)
            continue
        t = decode(strip_lead_codes(val) if first else val)
        if not first:
            t = t.lstrip('\u3000')
        first = False
        s.append(t)
    return ''.join(s).strip()


def extract_entry(data):
    boxes = []
    cur = None
    in_name = False
    for cmd, ws in toks(data):
        if cmd == C_NAME:
            in_name = True
            continue
        if cmd == C_BOX:
            if cur is not None:
                boxes.append(cur)
            cur = [('t', ws)]
            in_name = False
            continue
        if cmd in (C_SEP, C_END):
            if cur is not None:
                boxes.append(cur)
            cur = None
            in_name = False
            continue
        if in_name or cur is None:
            continue
        if cmd == C_BR:
            cur.append(('t', ws))
        elif cmd in TEXT_CMDS:      # 同一框内的另段文本（不同显示样式）
            cur.append(('t', ws))
        elif cmd == C_SURNAME:
            cur.append(('n', NAME_SURNAME))
            if ws:
                cur.append(('t', ws))
        elif cmd == C_GIVEN:
            cur.append(('n', NAME_GIVEN))
            if ws:
                cur.append(('t', ws))
    if cur is not None:
        boxes.append(cur)
    return boxes


# —— 交付层过滤 ——
# 1) 条目头部残留（≥3600 的随机码 / PUA）→ 整行丢弃
# 2) 系统・UI：章节跳过提示、教程入口/结束语、角色事件选择菜单
DROP_LINE = re.compile(
    r'\u3014\u672a\u89e3\u6790\u3015'          # 〔未解析〕（本作正文槽已全定值 ⇒ 只会是头部残留）
    r'|\uffe3{2,}'
    r'|[\u2261\u2225\u2282\u2234\u221e]'        # ≡∥⊂∴∞（头部噪声行）
)
SYS_LINE = re.compile(
    r'\u30b9\u30ad\u30c3\u30d7\u3057\u307e\u3059\u304b'            # スキップしますか
    r'|^\u4ee5\u4e0a\u3067\u30c1\u30e5\u30fc\u30c8\u30ea\u30a2\u30eb'  # 以上でチュートリアル
    r'|^\u30d2\u30f3\u30c8\u306f'                                # ヒントは
    r'|\u30c1\u30e5\u30fc\u30c8\u30ea\u30a2\u30eb\u3092\u898b\u307e\u3059\u304b'  # チュートリアルを見ますか
    r'|\u3069\u306e\u30ad\u30e3\u30e9\u30af\u30bf\u30fc\u306e\u30a4\u30d9\u30f3\u30c8'  # どのキャラクターのイベント
)

# 选项框的装饰括号（与正文同流、单独成框或作首字符）
FRAME_CLOSE = '\u3015\u3011\u300b\u3009\u3017'          # 〕 】 》 〉 〗（不含 』）
FRAME_ANY = '\u3014\u3015\u3010\u3011\u300a\u300b\uff3b\uff3d\u3008\u3009' \
            '\uff0b\uff0d\uff1c\uff1e'                  # 〔〕【】《》［］〈〉＋－＜＞
# 选项按钮的装饰字形（游戏码 1..90 段的标点槽被当图标用；逐例来自实测）
OPT_ICON = FRAME_ANY + FRAME_CLOSE + \
    '\u2260\u2642\uff5b\uff5c\u201d\u2018\uff5e\uff1c\uff1b\uff1a\u309c\uff1f' \
    '\uff40\u00a8\u00b4\uff3e\uffe3\uff3f\u30fd\u30fe\u309d\u309e\u3003\u4edd\u3006\u3007' \
    '\u30fc\u3001\u3002\uff0c\uff0e\u30fb'
HAS_WORD = re.compile(r'[\u3041-\u3096\u30a1-\u30f6\u4e00-\u9fff\uff10-\uff5a0-9A-Za-z]')
START_WORD = re.compile(r'^[\u3041-\u3096\u30a1-\u30f6\u4e00-\u9fff\uff10-\uff5a0-9A-Za-z\u300c\u300e\uff08]')


def main():
    src, dst = sys.argv[1], sys.argv[2]
    c = CPK(src)
    entries = sorted([e for e in c.entries if e['name'] and e['name'].isdigit()],
                     key=lambda e: int(e['name']))
    lines = []
    for e in entries:
        for parts in extract_entry(c.raw(e)):
            s = render(parts)
            if not s:
                continue
            # 选项装饰：行首收括号／按钮图标剥掉（剥后须立即是正文起首）
            while len(s) > 1 and s[0] in OPT_ICON and START_WORD.match(s[1:]):
                s = s[1:]
            if len(s) > 1 and s[0] == '\u300e' and '\u300f' not in s:
                s = s[1:]
            if DROP_LINE.search(s) or SYS_LINE.search(s):
                continue
            if any(0xE000 <= ord(ch) <= 0xF8FF for ch in s):
                continue
            # 纯装饰符号行（选项框括号等）：无假名/汉字/数字且不构成完整引号
            if not HAS_WORD.search(s) and len(s) <= 4 \
                    and not (s.startswith('\u300c') and s.endswith('\u300d')):
                continue
            lines.append(s)
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('entries', len(entries), 'lines', len(lines), '->', dst)


if __name__ == '__main__':
    main()
