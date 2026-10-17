#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vitamin X to Z (PSP, ULJS00347, HuneX「IKA SEQ SYSTEM v4.1」) 全文本提取。

源：PSP ISO9660 → PSP_GAME/USRDIR/DATA/GAMEDT.AFS（CRI AFS，8 成员）
  [0] 95 MB HFU2×987 —— 立绘/暂停画面包（块内再嵌 HFU2，含 TTH/EFF/ANM），非文本
  [1] 27 MB HFU2×220 —— 同上（贴图/特效包），非文本
  [2] 1.5 MB HFU2×90  —— ★剧本（本作全部正文；块 = 场景脚本，IKA SEQ v4.1）
  [3] 8.4 MB HFU2×91  —— IKA SEQPACK（演出时间轴，无文本）
  [4]-[7] 嵌套 AFS    —— SE / BGM / VOICE_X / VOICE_Z（AT3）

文本命令（本作实测，白名单 4 条）：
  0x3E n=1  名前札（含宏 ＠=姓 / ＄=名 / ★=地の文札）→ 丢（§0 不加说话人）
  0x3C n=3  台詞・独白                                      → 收
  0x44 n=3  地の文                                          → 收
  0x41 n=4  選択肢（连排=同组；其后参数为写入值，丢）        → 收

★ 两个主人公（同一对宏，按剧本段切换）：
  X編（冬・スキー補習合宿）＝南 悠里   ⇒ ＠→南　＄→悠里
  Z編（夏・臨海学校／愛染町）＝北森 真奈美 ⇒ ＠→北森　＄→真奈美
  依据：ELF EBOOT.dec @0x1885c4 串池 `＄`/`悠里`/`南`/`真奈美`/`北森`/`★`；
        @0x167c90 名字长度报错串 `<%c%c>`（恰两枚宏）；正文 `＠＄先生杯`／`＠＄です`（全名序=姓+名）。

控制码：`@n`＝框内软换行 → 合并；`@k…@w`＝着色（564 对）→ 去标记留字。
引号：原文 0 处 `「」`（仅 210 组 `『』`，均衡）⇒ 引擎不上引号，本作无需补 `「`。

用法：python scripts/vitaminxz_extract.py <GAMEDT.AFS> <out.txt>
"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arcanafesta_extract import decode_hfu2

SCRIPT_MEMBER = 2
NAME_CMDS = {0x3E}
TEXT_CMDS = {0x3C, 0x44}
CHOICE_CMD = 0x41
STR_CMDS = NAME_CMDS | TEXT_CMDS | {CHOICE_CMD}

# 侧别判据（名札整字相等）：X＝B6 生；Z＝A4/P2 生
X_PLATES = {'翼', '瞬', '一', '瑞希', '悟郎', '清春', '七瀬'}
Z_PLATES = {'天十郎', '慧', '千聖', '八雲', '那智', 'アラタ'}
X_KW = ('スキー', 'スノボ', '雪', '冬', 'ゲレンデ')
Z_KW = ('海', '夏', '臨海', '愛染', '祭')

NAMES = {'X': {'＠': '南', '＄': '悠里'}, 'Z': {'＠': '北森', '＄': '真奈美'}}


def afs_member(data, idx):
    n = struct.unpack_from('<I', data, 4)[0]
    o, s = struct.unpack_from('<II', data, 8 + idx * 8)
    return data[o:o + s]


def iter_records(stream):
    """自定界走查：仅白名单命令 + L 校验 + 双 NUL 收尾。产出 (cmd, txt)。"""
    i, N = 0, len(stream)
    while i < N - 6:
        if stream[i] == 0x26 and stream[i + 2] == 0x24 and stream[i + 4] == 0x5C:
            cmd = stream[i + 1]
            if cmd in STR_CMDS:
                L = stream[i + 5]
                if 4 <= L <= 900 and i + 4 + L <= N \
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


def clean(t, side):
    t = t.replace('@n', '')            # 框内软换行：合并
    t = t.replace('@k', '').replace('@w', '')  # 着色标记
    for mac, rep in NAMES[side].items():
        t = t.replace(mac, rep)
    return t.replace('★', '').strip()


def side_of(plates, body):
    xs = sum(1 for p in plates if p in X_PLATES)
    zs = sum(1 for p in plates if p in Z_PLATES)
    if xs != zs:
        return 'X' if xs > zs else 'Z'
    kx = sum(body.count(k) for k in X_KW)
    kz = sum(body.count(k) for k in Z_KW)
    return 'X' if kx >= kz else 'Z'


def main():
    afs, out = sys.argv[1], sys.argv[2]
    data = open(afs, 'rb').read()
    assert data[:4] == b'AFS\x00', data[:4]
    mem = afs_member(data, SCRIPT_MEMBER)
    assert mem[:4] == b'HFU2', mem[:4]
    blocks = decode_hfu2(mem)

    lines, stat = [], {'block': 0, 'plate': 0, 'text': 0, 'choice': 0}
    for bi, blk in enumerate(blocks):
        if bi == 0:                     # 块 0＝系统表（キャラ→失敗ボイス），非正文
            continue
        recs = list(iter_records(blk))
        plates = [t for c, t in recs if c in NAME_CMDS]
        body = ''.join(t for c, t in recs if c in TEXT_CMDS)
        side = side_of(plates, body)
        stat['block'] += 1
        for cmd, txt in recs:
            if cmd in NAME_CMDS:
                stat['plate'] += 1
                continue
            s = clean(txt, side)
            if not s:
                continue
            if cmd in TEXT_CMDS:
                stat['text'] += 1
            else:
                stat['choice'] += 1
            lines.append(s)

    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('blocks', stat['block'], 'plates', stat['plate'],
          'text', stat['text'], 'choice', stat['choice'], 'lines', len(lines))


if __name__ == '__main__':
    main()
