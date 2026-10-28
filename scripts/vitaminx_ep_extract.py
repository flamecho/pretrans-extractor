#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ビタミンX Evolution Plus（PSP, ULJS00325, HuneX「IKA SEQ SYSTEM v4.1」）全文本提取。

源：PSP ISO9660 → PSP_GAME/USRDIR/DATA/GAMEDT.AFS（CRI AFS，6 成员）
  [0] 77.8 MB HFU2×830 —— 立绘/暂停画面场景包（块内再嵌 HFU2），非文本
  [1] 92.7 MB 嵌套 AFS   —— SE / VOICE（`80 00 07 fc` 头）
  [2] 23.7 MB HFU2×175 —— 表情/状态表（真壁翼 / 通常・真剣・喜び / 恋愛値・偏差値）＝UI，非正文
  [3]  4.1 MB HFU2×367 —— ★剧本（367 块＝场景脚本，块内 `IKA SEQ SYSTEM  v4.1 HuneX 2010`）
  [4] 14.2 MB HFU2×367 —— 演出时间轴（无 IKA 串记录）
  [5]  2.5 MB 嵌套 AFS   —— 二进制资源

文本命令（本作实测）：
  0x3E n=1  名前札（`★`＝地の文の名札）                    → 丢（§0 不加说话人）
  0x3C n=3  台詞                                            → 收
  0x44 n=3  地の文                                          → 收
  0x41 n=4  選択肢（連続３条＝同组；其后 0x3C 为所选台词）  → 收
  0xBE n=2  ツッコミ選択肢（ZAPP_SENTAKU，成对２条）        → 收

断框（L0）：每条文本记录前恒有 `26 05 24 00`（换页/清框）——57,419/57,419 命中；
  记录内 `@n`＝框内软换行 ⇒ 合并。无「不清框等待按键」变体 ⇒ 单版本产出。

主角宏：`＠`＝姓 南、`＄`＝名 悠里（`＠＄です` 自介序＝姓+名；`＠先生`/`＠チャン`；
  默认名取自 EBOOT.dec 串池 `南\\0\\0悠里\\0\\0`，可改名）。

用法：python scripts/vitaminx_ep_extract.py <GAMEDT.AFS> <out.txt>
"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arcanafesta_extract import decode_hfu2

SCRIPT_MEMBER = 3
NAME_CMDS = {0x3E}
TEXT_CMDS = {0x3C, 0x44}
CHOICE_CMDS = {0x41, 0xBE}
STR_CMDS = NAME_CMDS | TEXT_CMDS | CHOICE_CMDS

MACROS = {'＠': '南', '＄': '悠里'}


def afs_member(data, idx):
    o, s = struct.unpack_from('<II', data, 8 + idx * 8)
    return data[o:o + s]


def iter_records(stream):
    """自定界走查：白名单命令 + L 校验 + 双 NUL 收尾。产出 (cmd, txt)。"""
    i, N = 0, len(stream)
    while i < N - 6:
        if stream[i] == 0x26 and stream[i + 2] == 0x24 and stream[i + 4] == 0x5C:
            cmd = stream[i + 1]
            if cmd in STR_CMDS:
                L = stream[i + 5]
                if 4 <= L <= 2000 and i + 4 + L <= N \
                        and stream[i + 4 + L - 2] == 0 and stream[i + 4 + L - 1] == 0:
                    try:
                        txt = stream[i + 6:i + 4 + L - 2].decode('cp932')
                    except UnicodeDecodeError:
                        i += 1
                        continue
                    yield cmd, txt
                    i += 4 + L
                    continue
        i += 1


def clean(t):
    t = t.replace('@n', '')                      # 框内软换行 → 合并
    for mac, rep in MACROS.items():
        t = t.replace(mac, rep)
    t = t.replace('★', '')                       # 地の文の名札
    return t.rstrip(' \t\u3000\r\n')


def main():
    afs, out = sys.argv[1], sys.argv[2]
    data = open(afs, 'rb').read()
    assert data[:4] == b'AFS\x00', data[:4]
    mem = afs_member(data, SCRIPT_MEMBER)
    assert mem[:4] == b'HFU2', mem[:4]
    blocks = decode_hfu2(mem)

    lines, stat = [], {'block': 0, 'plate': 0, 'text': 0, 'choice': 0}
    for bi, blk in enumerate(blocks):
        if bi == 0:                              # 块 0＝失敗ボイス表，非正文
            continue
        stat['block'] += 1
        for cmd, txt in iter_records(blk):
            if cmd in NAME_CMDS:
                stat['plate'] += 1
                continue
            s = clean(txt)
            if not s.strip():
                continue
            stat['choice' if cmd in CHOICE_CMDS else 'text'] += 1
            lines.append(s)

    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('blocks', stat['block'], 'plates', stat['plate'],
          'text', stat['text'], 'choice', stat['choice'], 'lines', len(lines))


if __name__ == '__main__':
    main()
