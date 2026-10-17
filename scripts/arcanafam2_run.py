#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""アルカナ・ファミリア2 (PSP, HuneX「IKA SEQ SYSTEM v4.2」) 全文本提取。

源：PSP ISO9660 → PSP_GAME/USRDIR/DATA/GAMEDT.AFS（CRI AFS，8 成员）
  AFS[2] = SCRIPT（HFU2 ×226，X=0x1000，逐块 UFFA+经典 Okumura LZSS）——文本只在这里
  AFS[0] 165B／AFS[1] 表情动画（解压后图像噪声）／AFS[3] 媒体／AFS[4-7] 嵌套 AFS（SE/BGM/VOICE）
容器/解码复用 arcanafesta_extract（同族压缩变体）。

★★ 本作关键修正：字符串记录**必须按命令白名单**识别。
  同族前两作用「`26 ?? 24 ?? 5C <L>` 自定界扫描」即可，但本作有 `0x34 n=1`（発話者ID）
  `0x0c n=1`（ラベル定義）等命令，其 **u16 操作数首字节恰为 0x5C**（77/20 处），
  L 校验偶有巧合通过 → 匹配器前进会**吞掉其后的名札+台词**（实测少 1 框）。
  实测「L 校验 100% 通过」的命令恰为 {0x3C,0x3E,0x41,0x4C,0x4D} ⇒ 以白名单定字符串记录。

文本命令（本作实测；★＝字符串不在 +4 而在参数列表末尾 off=14）：
  0x3C n=3  台詞/地の文          → 收（29,285）
  0x3E n=1  名前札               → 丢（§0 不加说话人）（29,267）
  0x41 n=4  選択肢（连排=同组）   → 收（671；其后参数为写入值，丢）
  0x4C n=1  複数名札             → 丢（55）
  0x4D n=1  複数名の後のセリフ    → 收（55）
  ★0xA7 n=8  心の声/独白（7int＋串）→ 收（390；与主线重复率仅 3.1%＝独立正文）
  ★0x50 n=6  バトルコマンド（後接 #BATTLE_SUCCSESS 标签）→ 收（55；「避けろ！」等直上屏指令）
  （0x34 n=1＝発話者ID2B／0x0c n=1＝ラベル定義／0xC6 等：非字符串，丢）

控制码：`@n`＝框内软换行 → 合并。
姓名槽宏：全角＄(U+FF04)＝可改名槽；ELF `EBOOT.BIN.dec` @0x17c0cc 有槽表
  `＄フェリチータ`／`＄フェル`／`＄フクロータ` ＋ 对应默认名 ⇒ 删＄、留默认名 inline。
引号：原文用『』（711/711 均衡），`「」`=0。
用語辞典：无（AFS 各成员无成句日文；ELF `辞典`/`ワード`=0，`用語集` 仅系统通知串）。
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arcanafesta_extract import parse_iso_afs, parse_afs_members, decode_hfu2

STR_CMDS = {0x3C, 0x3E, 0x41, 0x4C, 0x4D}      # 字符串在 +4
STR_CMDS_OFF14 = {0xA7, 0x50}                    # 字符串在 +18（7×u16 参数之后）
TEXT_CMDS = {0x3C, 0x4D, 0xA7, 0x50}
CHOICE_CMD = 0x41
NAME_CMDS = {0x3E, 0x4C}
NAME_SLOT_MACRO = '\uff04'   # 全角＄


def iter_str_records(stream):
    """仅识别白名单命令的字符串记录；自定界，永不失步。产出 (pos, cmd, txt)。

    白名单保证「u16 操作数首字节恰为 0x5C」的假阳性（本作 0x34/0x0c/0xC6…共 115 处）
    不会被当字符串——否则匹配器前进会吞掉其后的正文。
    ★ 0xA7/0x50 的字符串位于参数列表末尾（+18），须单独按偏移取。
    """
    i, N = 0, len(stream)
    while i < N - 6:
        if stream[i] == 0x26 and stream[i + 2] == 0x24:
            cmd = stream[i + 1]
            if cmd in STR_CMDS and stream[i + 4] == 0x5C:
                L = stream[i + 5]
                if 4 <= L <= 600 and i + 4 + L <= N \
                        and stream[i + 4 + L - 2] == 0 and stream[i + 4 + L - 1] == 0:
                    try:
                        txt = stream[i + 6:i + 4 + L - 2].decode('cp932')
                    except UnicodeDecodeError:
                        i += 1
                        continue
                    yield (i, cmd, txt)
                    i += 4 + L
                    continue
            elif cmd in STR_CMDS_OFF14 and i + 18 < N and stream[i + 18] == 0x5C:
                L = stream[i + 19]
                if 4 <= L <= 900 and i + 18 + L <= N \
                        and stream[i + 18 + L - 2] == 0 and stream[i + 18 + L - 1] == 0:
                    try:
                        txt = stream[i + 20:i + 18 + L - 2].decode('cp932')
                    except UnicodeDecodeError:
                        i += 1
                        continue
                    yield (i, cmd, txt)
                    i += 18 + L
                    continue
        i += 1


def extract_lines(blob):
    lines, stats = [], {}
    for pos, cmd, txt in iter_str_records(blob):
        stats[cmd] = stats.get(cmd, 0) + 1
        if cmd in NAME_CMDS:
            continue
        if cmd in TEXT_CMDS or cmd == CHOICE_CMD:
            lines.append(txt.replace('@n', '').replace(NAME_SLOT_MACRO, ''))
    return lines, stats


def main():
    iso = sys.argv[1]
    outpath = sys.argv[2] if len(sys.argv) > 2 else \
        '提取结果/アルカナファミリア2_全文本.txt'
    afs = parse_iso_afs(iso)
    mems = parse_afs_members(afs)
    off, size = mems[2]
    blob = b''.join(decode_hfu2(afs[off:off + size]))
    lines, stats = extract_lines(blob)
    print('script AFS[2] decoded=%d' % len(blob))
    print('stats=%s' % {hex(k): v for k, v in sorted(stats.items())})
    print('lines=%d' % len(lines))
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    with open(outpath, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('wrote %s' % outpath)


if __name__ == '__main__':
    main()
