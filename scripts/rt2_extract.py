#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ラディアンテイル ～ファンファーレ！～ (NS) STCM2L 文本提取  —— 2026-10-26 修正版

链路：NSP → NCA → romfs/CONTENTS/STORY.cpk → SCRIPT/*.DAT（STCM2L, UTF-8，构建串 Apr 12 2018）
指令：[u32 func][u32 argc][u32 len] + argc×[p0,p1,p2]（`CODE_START_` 后 0x10 起）
串记录：[L/4][1][L][utf8][NUL][pad]（12B 头，另有 16/24B 变体，readrec 三档兼容）

本作 opcode（全库普查得出）：
  0x17260 = 正文（一框的第 1..n 段，收）
  0x4f134 = 正文·双版本一框 argc=8：[0][明文×3][4][#Name[1]×3]  → 收明文槽 1..3
  0x4faf4 = 同上（argc=8，明文在槽 2/3）                        → 收明文槽 1..3
  0x4f80c = 正文·双版本一框 argc=4：[0][明文][2][#Name[1]]      → 收明文槽 1..3
  0x17a6c = 名札（丢弃，**同时是新消息＝新点击的断点**）
  0x1f4   = 等待点击＝收框
  0x9fac / 0x9dc4 = switch（分支）⇒ **也是断点**（台词→地の文 就是靠它断开）

★★ 2026-10-27 断框判据修正（与 ラディアンテイル 本体同一坑）：
  旧版只在 0x1f4 处 flush ⇒ 同一 0x1f4 周期里「地の文 + 台词 / 地の文 + 心声」被并成一行（实测 251 处，
  最长行 148 宽）。正解：**一行 = 一段「连续 BODY 记录」**，SEPS 里任一 op 都断行；
  分支互斥产生的相邻同句（同一句在 if/else 两侧各写一遍）只留一条。

★ 修正要点（2026-10-26）：
  1) 旧版把 0x4f134 当「富文本宏串」整条丢弃 → 丢失 302 行整句（主角名在此）。
  2) 旧版 clean() 先剥宏，把名字宏 #Name[1] 一起吃掉了 → 54 行断句（「オレの中でが、」）。
     现在：先把 #Name[1] 还原成 ティファリア，再剥 #Type/#Color/#Scale 等装饰宏。

用法: python scripts/rt2_extract.py [SCRIPT目录] [输出txt]
"""
import glob
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sympathy_extract import walk, is_text

SRC = sys.argv[1] if len(sys.argv) > 1 else '_w_ff2/story/SCRIPT'
OUT = sys.argv[2] if len(sys.argv) > 2 else '提取结果/[NS-JP]ラディアンテイル ～ファンファーレ！～.txt'

BODY = {0x17260}
SEPS = {0x1f4, 0x9fac, 0x9dc4, 0x17a6c}   # 收框 / switch / switch / 名札
BRANCH = {0x9fac, 0x9dc4, 0x6, 0x0}       # 分支类：其后的相邻同句视为互斥两版 ⊕
DUAL8 = {0x4F134, 0x4FAF4}     # 明文在槽 1..3，宏版在槽 5..7
DUAL4 = {0x4F80C}              # 明文在槽 1，  宏版在槽 3
NAME = 'ティファリア'
DROP = {'シーンを選択してください'}   # シーン選択メニューのプロンプト（UI）
MACRO = re.compile(r'#[A-Za-z][A-Za-z0-9_]*(?:\[[^\]]*\])?')


def dedup(s):
    """同一框内因分支重复出现的整句折半（旧成品既有行为）。"""
    while len(s) >= 2 and len(s) % 2 == 0 and s[:len(s) // 2] == s[len(s) // 2:]:
        s = s[:len(s) // 2]
    return s


def clean(s):
    s = s.replace('#Name[1]', NAME)          # ★ 先还原名字
    s = MACRO.sub('', s)                     #   再剥装饰宏
    s = s.replace('\\n', '').replace('\r', '')
    return dedup(s.strip())


def main():
    files = sorted(glob.glob(os.path.join(SRC, '*.DAT')),
                   key=lambda p: int(re.sub(r'\D', '', os.path.basename(p)) or 0))
    lines = []
    for f in files:
        d = open(f, 'rb').read()
        if not d.startswith(b'STCM2L'):
            print('  [skip] 非 STCM2L:', os.path.basename(f))
            continue
        cur = []

        sep = [None]

        def flush():
            if cur:
                t = clean(''.join(cur))
                cur.clear()
                if t and t not in DROP:
                    if lines and t == lines[-1] and sep[0] in BRANCH:
                        pass                    # ★ 分支互斥两版同句 ⇒ 只留一条
                    else:
                        lines.append(t)

        for op, ss in walk(d):
            if op in BODY:
                for s in ss:
                    if s and is_text(s):
                        cur.append(s)
            elif op in DUAL8:
                for s in ss[1:4]:
                    if s and is_text(s):
                        cur.append(s)
            elif op in DUAL4:
                for s in ss[1:3]:
                    if s and is_text(s):
                        cur.append(s)
            elif op in SEPS:
                sep[0] = op
                flush()
        sep[0] = None
        flush()

    os.makedirs(os.path.dirname(OUT) or '.', exist_ok=True)
    with io.open(OUT, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(lines) + '\n')
    print('lines', len(lines))
    print('ティファリア', sum(1 for l in lines if NAME in l), '行 /',
          sum(l.count(NAME) for l in lines), '次')


if __name__ == '__main__':
    main()
