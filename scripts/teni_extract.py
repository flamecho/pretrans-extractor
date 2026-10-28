#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""新テニスの王子様 LET'S GO!! 〜Daily Life〜 from RisingBeat (NS, HuneX Ogre) → 全文本

正文：romfs/allscr.mrg（mrgd00，1197 成员）里的 `_ZM<5-6hex>(正文)` —— 一条 = 一个文本框。
  正文编码 **UTF-8**（不是 cp932）；`^`＝框内软换行（合并）；`@n`＝框内暂停（删）；
  `<基底語,読み>`＝注音（取基底語）；`_MTLK(1,名前)`＝名札（不收）。
  `allscr_d.mrg` 是**调试/菜单脚本**（`デバッグメニューへ戻る` 等），整体不收。
非剧情脚本判定：既无 `_VPLY`（语音）也无 `_MTLK`（名札）的成员一律视为系统/调试。
"""
import os
import re
import struct
import sys

sys.path.insert(0, 'tools')
from ozmafia_extract import mrgd00_members, mzx0_decompress

ROMFS = '_w_W3_teni/romfs'
OUT = '提取结果/[NS-JP]新テニスの王子様 LET’S GO!! 〜Daily Life〜 from RisingBeat.txt'

ZM = re.compile(r'^_ZM[0-9a-fA-F]{5,6}\((.*)$')
SELR = re.compile(r'^_SELR\(\d+,(.*)$')
RUBY = re.compile(r'<([^<>,]*),[\u3040-\u309f\u30a0-\u30ffー]+>')


def clean(s):
    s = RUBY.sub(r'\1', s)
    s = s.replace('@n', '').replace('^', '')
    s = s.replace('\r', '').replace('\n', '')
    return s.strip()


def main():
    blob = open(os.path.join(ROMFS, 'allscr.mrg'), 'rb').read()
    cnt, mem = mrgd00_members(blob)
    lines = []
    n_zm = n_opt = 0
    for i in range(3, cnt):
        b = mem[i]
        if b[:4] == b'MZX0':
            e = struct.unpack('<L', b[4:8])[0]
            t = mzx0_decompress(b[8:], len(b) - 8, e).decode('utf-8', 'replace')
        else:
            t = b.decode('utf-8', 'replace')
        if '_VPLY' not in t and '_MTLK' not in t:
            continue
        if 'DEBUG' in t or 'デバッグ' in t or 'チェック_' in t:
            continue
        for st in t.split(';'):
            st = st.strip().rstrip(')')
            m = ZM.match(st)
            if m:
                s = clean(m.group(1))
                if s:
                    lines.append(s)
                    n_zm += 1
                continue
            m = SELR.match(st)
            if m:
                s = clean(m.group(1).split(',')[0])   # _SELR(idx,選択肢,名前1,名前2) ⇒ 只取选项本体
                if s:
                    lines.append(s)
                    n_opt += 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(lines) + '\n')
    print('ZM %d  选项 %d  总行 %d' % (n_zm, n_opt, len(lines)))


if __name__ == '__main__':
    main()
