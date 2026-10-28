#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""スチームプリズン (NS, HuneX Ogre) allscr.mrg + script_text.mrg → 全文本

链路：XCI → NCA → romfs → allscr.mrg（脚本，MZX0）＋ script_text.mrg（文本表，JP 表 = member[1]）

指令（';' 分隔）：
  _ZM<6hex>($NNNNNN)        一次点击 = 一个文本框（文本表下标）
  _MSAD($NNNNNN^)           同框续写（前一条的接续 ⇒ 合并）
  _SELR(idx,$NNNNNN)        选项（连续若干条，到 _SELD 收）
  _LVSV($NNNNNN)            章节标题
  _MTLK(1,id)               说话人名札（不收）

文本表：`script_text.mrg` 由 8 个成员组成 —— [0]/[2]/[4] 下标表（BE u32 字节偏移），
[1] 日本語 / [3] English / [5] 中文（本文只用 [1]）。
"""
import sys
import os
import re
import struct

sys.path.insert(0, 'tools')
from ozmafia_extract import mrgd00_members, mzx0_decompress

ROMFS = '_w_W3_steam/romfs'
OUT = '提取结果/[NS-JP]スチームプリズン.txt'
HERO = '**AA'          # 主角名占位符（可改名，游戏内未存默认名）

EXCLUDE = {'MAIN', 'SUB_SCRIPT'}
EXCLUDE_PREFIX = ('MOVIE',)

ZM_RE = re.compile(r'^_ZM[0-9a-fA-F]{5}\(\$(\d{6})\^?\)')
MSAD_RE = re.compile(r'^_MSAD\(\$(\d{6})\^?\)')
SELR_RE = re.compile(r'^_SELR\(\d+,\$(\d{6})\)')
LVSV_RE = re.compile(r'^_LVSV\(\$(\d{6})\)')
RUBY = re.compile(r'<([^<>,]*),[\u3040-\u309f\u30a0-\u30ffー]+>')
HANK = re.compile(r'[\uff61-\uff9f]+')


def load_jp():
    blob = open(os.path.join(ROMFS, 'script_text.mrg'), 'rb').read()
    cnt, mem = mrgd00_members(blob)
    jp, idx = mem[1], mem[0]
    n = len(idx) // 4
    offs = [int.from_bytes(idx[i * 4:i * 4 + 4], 'big') for i in range(n)]
    out = []
    for i in range(n):
        a = offs[i]
        b = offs[i + 1] if i + 1 < n else len(jp)
        out.append(jp[a:b].decode('utf-8', 'replace').rstrip('\r\n'))
    return out


def clean(t):
    t = RUBY.sub(r'\1', t)
    t = HANK.sub(lambda m: __import__('unicodedata').normalize('NFKC', m.group()), t)
    t = t.replace('\n', '').replace('\r', '')
    return t.strip()


def main():
    jp = load_jp()
    blob = open(os.path.join(ROMFS, 'allscr.mrg'), 'rb').read()
    cnt, mem = mrgd00_members(blob)
    nam = mem[0]
    names = [nam[i:i + 32][:30].rstrip(b'\x00').decode('cp932', 'replace')
             for i in range(0, len(nam) - 31, 32)]
    names = [n for n in names if n.strip()]

    lines = []
    n_zm = n_msad = n_opt = n_title = 0
    last_text = ''
    missing = 0
    for i, nm in enumerate(names):
        if nm in EXCLUDE or nm.startswith(EXCLUDE_PREFIX):
            continue
        b = mem[3 + i]
        if b[:4] == b'MZX0':
            ex = struct.unpack('<L', b[4:8])[0]
            raw = mzx0_decompress(b[8:], len(b) - 8, ex)
        else:
            raw = b
        t = raw.decode('cp932', 'replace')
        sel = []
        pend_name = False
        for st in t.split(';'):
            st = st.strip()
            if not st:
                continue
            m = ZM_RE.match(st)
            if m:
                k = int(m.group(1))
                if k >= len(jp) or not jp[k]:
                    missing += 1
                    continue
                if sel:
                    for _, oid in sel:
                        lines.append(clean(jp[oid]))
                        n_opt += 1
                    sel = []
                lines.append(clean(jp[k]))
                n_zm += 1
                pend_name = False
                last_text = clean(jp[k])
                continue
            m = MSAD_RE.match(st)
            if m:
                k = int(m.group(1))
                if k < len(jp) and jp[k]:
                    n_msad += 1
                    # 2026-10-26 修：_MSAD 是「同框追加一条」＝**一次点击**，
                    # 只有「上一条引号未闭合」（真续写同一句）才并入；实测 4,088 条中仅 148 条属此。
                    # 判据用「上一条文本原文」的引号是否未闭合（不能用已合并的输出行，那会把状态带歪）
                    t = clean(jp[k])
                    prev_unclosed = bool(last_text) and last_text.count('「') > last_text.count('」')
                    if pend_name or not lines or prev_unclosed:
                        lines.append(t)
                        n_zm += 1
                    else:
                        lines[-1] += t
                    last_text = t
                    pend_name = False
                continue
            m = SELR_RE.match(st)
            if m:
                sel.append((len(sel), int(m.group(1))))
                continue
            m = LVSV_RE.match(st)
            if m:
                k = int(m.group(1))
                if k < len(jp) and jp[k]:
                    lines.append(clean(jp[k]))
                    n_title += 1
                continue
            if st.startswith('_MTLK'):
                pend_name = True
                continue
            if st.startswith('_SELD') or st.startswith('_GOTS'):
                if sel:
                    for _, oid in sel:
                        if oid < len(jp) and jp[oid]:
                            lines.append(clean(jp[oid]))
                            n_opt += 1
                    sel = []
        if sel:
            for _, oid in sel:
                if oid < len(jp) and jp[oid]:
                    lines.append(clean(jp[oid]))
                    n_opt += 1

    lines = [x for x in lines if x]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(lines) + '\n')
    print('ZM %d  MSAD %d  选项 %d  标题 %d  → 总行 %d  缺文本 %d'
          % (n_zm, n_msad, n_opt, n_title, len(lines), missing))


if __name__ == '__main__':
    main()
