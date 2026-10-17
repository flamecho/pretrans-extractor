#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""アルカナ・ファミリア 幽霊船の魔術師 (PSP, HuneX「IKA SEQ SYSTEM v3.4」) 全文本提取。

源：PSP ISO9660 → PSP_GAME/USRDIR/DATA/GAMEDT.AFS（CRI AFS，7 成员）
  AFS[2] = SCRIPT（HFU2 ×126，X=0x800，逐块 UFFA+LZSS）——文本只在这里
  AFS[0]/[1]/[3] 解压后为 表情动画/二进制/CRI 内嵌归档（无剧本文本）
容器/解码复用 arcanafesta_extract（同族压缩变体：UFFA + 经典 Okumura LZSS）。
字节码：指令 `26 <cmd> 24 <nargs>`；字符串记录 `5C <L> <SJIS L-4> 00 00`
文本命令（本作实测，与 フェスタ・レガーロ 不同）：
  0x3E n=1  名前札           → 丢（§0 不加说话人）
  0x4C n=1  複数名札(リベルタ他) → 丢
  0x3C n=3  台詞/地の文        → 收
  0x4D n=1  複数名の後のセリフ   → 收
  0x41 n=4  選択肢（连排=同组）  → 收（其后参数为写入值，丢）
控制码：`@n`＝框内软换行 → 合并；`＄`＝姓名槽插入宏（后接默认名）→ 去宏留名。
"""
import sys, os, struct

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arcanafesta_extract import (parse_iso_afs, parse_afs_members, decode_hfu2,
                                 iter_str_records)

TEXT_CMDS = {0x3C, 0x4D}
CHOICE_CMD = 0x41
NAME_CMDS = {0x3E, 0x4C}

# 原文笔误修正（整行定值表；见 skill 00b ⑧）
LINE_FIXES = {
    '『お嬢！お嬢様……': '『お嬢！お嬢様……』',   # 0x83e74：缺闭合 』（全篇唯一不配对）
}


def extract_lines(blob):
    lines, stats = [], {}
    for pos, cmd, nargs, txt in iter_str_records(blob):
        stats[cmd] = stats.get(cmd, 0) + 1
        if cmd in NAME_CMDS:
            continue
        if cmd in TEXT_CMDS or cmd == CHOICE_CMD:
            s = txt.replace('@n', '').replace('＄', '')
            s = LINE_FIXES.get(s, s)
            lines.append(s)
    return lines, stats


def main():
    iso = sys.argv[1]
    outpath = sys.argv[2] if len(sys.argv) > 2 else \
        '提取结果/アルカナファミリア_幽霊船の魔術師_全文本.txt'
    afs = parse_iso_afs(iso)
    mems = parse_afs_members(afs)
    off, size = mems[2]
    blob = b''.join(decode_hfu2(afs[off:off + size]))
    lines, stats = extract_lines(blob)
    print('script blocks=126 decoded=%d' % len(blob))
    print('stats=%s' % {hex(k): v for k, v in sorted(stats.items())})
    print('lines=%d' % len(lines))
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    with open(outpath, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('wrote %s' % outpath)


if __name__ == '__main__':
    main()
