#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VitaminZ Graduation (PSP, ULJS00xxx v1.01, HuneX「IKA SEQ SYSTEM v4.2」) 全文本提取。

源：PSP ISO9660 → PSP_GAME/USRDIR/DATA/GAMEDT.AFS（CRI AFS，7 成员）
  [0] 78 MB HFU2×906 —— 立绘/暂停画面包（块内再嵌 HFU2，标签如 `教室　昼`），UI，非正文
  [1] 19 MB HFU2×104 —— 贴图/特效包，含 1 块系统脚本（設定/セーブ/用語 仅作菜单字样），无辞典
  [2]  1 MB HFU2×69  —— ★剧本（IKA SEQ v4.2 HuneX 2011；块 0＝開発テスト）
  [3]  9 MB HFU2×69  —— IKA SEQPACK BIN 2010（演出时间轴，无串）
  [4]-[6] 嵌套 AFS    —— SE / BGM / VOICE

文本命令（本作实测）：
  0x3E n=1  名前札（`＄`＝主人公 / `★`＝地の文札）→ 丢（§0 不加说话人）
  0x3C n=3  台詞・独白                                  → 收      12,697
  0x44 n=3  地の文                                      → 收       1,011
  0x41 n=4  選択肢（连排＝同组，后 3 参数为写入值）      → 收          90
  0xBC n=5  選択肢（第二种载体，后段场景改用此命令）     → 收          15

用語辞典（`#\tWORD_NNN\0` 标签 ＋ `5C L` 見出し ＋ `5C L` 解説，藏在贴图成员 [1]）：
  block 16＝29 条（本作 FD 术语：アホサイユ/Ａ４/ＧＥ/Ｐ２…，非五十音顺）
  block 36＝83 条（五十音顺总辞典：相沢悟/愛染アイドルフェスティバル/…，整块重复 2 份）
  两本 7 个词头重叠、措辞不同（Ａ４/Ｂ６/ＧＴＲ/Ｐ２/成宮財閥 有改写）⇒ 按 (見出し,解説) 去重后并入末尾。

★★ 主人公宏：`＠`＝姓（北森）／`＄`＝名（真奈美）
  依据 ① 自介句 `天十郎君、＠＄です。`（全名序＝姓+名，7 处）
       ② `＠先生` 141 处（学生称她「北森先生」）vs `＄先生` 6 处（恋人/アラタ 改称其名）
       ③ EBOOT.dec @0x189030 默认全名串 `北森　真奈美`；@0x1d1660 宏池 `＠`,`＄`,`真奈美`,`北森`,`★`
  主角＝北森 真奈美（vndb VitaminZ 主人公，本作 FD 中已毕业、回校任教育実習→担任）。

控制码：`@n`＝框内软换行（15,428 处）→ 合并；`@k…@w`＝着色（360 对）→ 去标记留字。
半角假名 0 处；`「」` 由原文自带。

用法：python scripts/vzgrad_extract.py <GAMEDT.AFS> <out.txt>
"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arcanafesta_extract import decode_hfu2

SCRIPT_MEMBER = 2
GLOSS_MEMBER = 1                  # 用語辞典藏在贴图成员（同 b6 作）
GLOSS_LABEL = b'WORD_'
SKIP_BLOCKS = {0}                 # 块 0＝開発テスト（18×「開発テスト表示」/「ふがっ！」/バレーボールa-e/実験）
NAME_CMDS = {0x3E}
TEXT_CMDS = {0x3C, 0x44}
CHOICE_CMDS = {0x41, 0xBC}
STR_CMDS = NAME_CMDS | TEXT_CMDS | CHOICE_CMDS

MACROS = {'＠': '北森', '＄': '真奈美'}


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
                if 4 <= L <= 1200 and i + 4 + L <= N \
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
    t = t.replace('@n', '')                          # 框内软换行：合并
    t = t.replace('@k', '').replace('@w', '')        # 着色标记
    for mac, rep in MACROS.items():
        t = t.replace(mac, rep)
    return t.replace('★', '').strip()


def iter_glossary(stream):
    """`#\\tWORD_NNN\\0` ＋ `5C L` 見出し ＋ `5C L` 解説。产出 (label, head, exp)。"""
    i = 0
    while True:
        j = stream.find(GLOSS_LABEL, i)
        if j < 0:
            return
        k = stream.index(b'\x00', j)
        label = stream[j:k].decode('ascii', 'replace')
        i = k + 1

        def take(p):
            if p >= len(stream) or stream[p] != 0x5C:
                return None, p
            L = stream[p + 1]
            if L < 4 or p + L > len(stream):
                return None, p
            try:
                return stream[p + 2:p + L - 2].decode('cp932'), p + L
            except UnicodeDecodeError:
                return None, p

        head, p = take(k + 1)
        exp, p2 = (take(p) if head is not None else (None, 0))
        yield label, head, exp


def main():
    afs, out = sys.argv[1], sys.argv[2]
    data = open(afs, 'rb').read()
    assert data[:4] == b'AFS\x00', data[:4]
    mem = afs_member(data, SCRIPT_MEMBER)
    assert mem[:4] == b'HFU2', mem[:4]
    blocks = decode_hfu2(mem)

    lines, stat = [], {'block': 0, 'plate': 0, 'text': 0, 'choice': 0, 'drop': 0}
    for bi, blk in enumerate(blocks):
        if bi in SKIP_BLOCKS:
            stat['block'] += 0
            continue
        stat['block'] += 1
        for cmd, txt in iter_records(blk):
            if cmd in NAME_CMDS:
                stat['plate'] += 1
                continue
            s = clean(txt)
            if not s:
                stat['drop'] += 1
                continue
            if cmd in TEXT_CMDS:
                stat['text'] += 1
            else:
                stat['choice'] += 1
            lines.append(s)

    # 用語辞典（并入末尾）
    gmem = afs_member(data, GLOSS_MEMBER)
    seen, gloss = set(), []
    for blk in decode_hfu2(gmem):
        for label, head, exp in iter_glossary(blk):
            if not head or not exp:
                continue
            key = (head, exp)
            if key in seen:
                continue
            seen.add(key)
            gloss.append('【%s】%s' % (clean(head), clean(exp)))
    if gloss:
        lines.extend(gloss)

    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('blocks', stat['block'], 'plates', stat['plate'], 'text', stat['text'],
          'choice', stat['choice'], 'empty', stat['drop'], 'glossary', len(gloss),
          'lines', len(lines))


if __name__ == '__main__':
    main()
