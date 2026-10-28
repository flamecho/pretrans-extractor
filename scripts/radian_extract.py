#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ラディアンテイル（本体，非 FD）—— STCM2L "May 18 2015" 变体 → 全文本。

链路：NSP → Program NCA(titlekek_0c) → romfs CONTENTS/STORY.cpk → SCRIPT/*.DAT（STCM2L）
指令流：[u32 func][u32 argc][u32 len] + argc×[p0,p1,p2]（`CODE_START_` 后 0x10 起，见 sympathy_extract.walk）
本作 opcode（全库普查 95 个 DAT / 85,825 条日文串）：
  0x146b0 = 正文（61,785 条）
  0x14dac = 名札（16,235 条，丢弃）
  0x1f4   = 等待点击 / 收框（**不是唯一断点**，见下）
  0x14dac = 名札 ⇒ **每条名札开头都是新消息＝新点击**（2026-10-27 修正）
  0x8d1c / 0x14bd4 = switch+end / 清名 ⇒ 同样是新消息（台词→地の文 就是靠它断开的）
  ⇒ 判据：**一行 = 两条 BODY 记录之间夹 0 个其它 op 的那一段**（SEPS 里任一 op 都断行）
  其它（0x43f70 资源名、0x8ef4/0x8b44 色変化判定、0x13ae4/0x162b0 标签）不取
"""
import glob, os, re, sys
sys.path.insert(0, 'tools')
from sympathy_extract import walk, is_text

SRC = '_w_W1_radian/story/SCRIPT'
OUT = '提取结果/[NS-JP]ラディアンテイル.txt'
BODY = {0x146b0, 0x435cc}   # 0x435cc = 同句的「直写名 / #Name[1]」双版本，成对出现
SEPS = {0x14dac, 0x8d1c, 0x14bd4, 0x1f4}   # 断点：名札 / switch+end / 清名 / 收框
DROP = {'ルートを選択してください'}
NAME = 'ティファリア'
MACRO = re.compile(r'#(?!Name\[)[A-Za-z][A-Za-z0-9_]*(?:\[[^\]]*\])?')
NAMEM = re.compile(r'#Name\[\d+\]')


def clean(s):
    s = NAMEM.sub(NAME, s)
    s = MACRO.sub('', s)
    s = s.replace('\\n', '').replace('\r', '')
    s = re.sub(r'\n[\u3000 ]?', '', s)
    return s.strip()


def main():
    files = sorted(glob.glob(os.path.join(SRC, '*.DAT')),
                   key=lambda p: int(re.sub(r'\D', '', os.path.basename(p)) or 0))
    lines = []
    for f in files:
        d = open(f, 'rb').read()
        if not d.startswith(b'STCM2L'):
            continue
        cur = []

        def flush():
            if len(cur) >= 2 and len(cur) % 2 == 0:
                h = len(cur) // 2
                # 直写名 / #Name 两版整段重复 ⇒ 只留一版（**按 clean 后比较**：两版只差名字，原文不等）
                if [clean(x) for x in cur[:h]] == [clean(x) for x in cur[h:]]:
                    del cur[h:]
            if cur:
                t = clean(''.join(cur))
                if t and t not in DROP:
                    lines.append(t)
                cur.clear()

        for op, ss in walk(d):
            if op in BODY:
                for s in (ss or []):
                    if s and is_text(s):
                        cur.append(s)
            elif op in SEPS:                    # ★ 名札 / switch+end / 清名 ⇒ 新消息（新点击）
                flush()
            elif op == 0x1f4:                   # 收框 / 等待点击
                flush()
        flush()
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(lines) + '\n')
    print('脚本 %d / 行 %d -> %s' % (len(files), len(lines), OUT))


if __name__ == '__main__':
    main()
