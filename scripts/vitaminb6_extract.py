#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VitaminX DetectiveB6 (PSP, HuneX「IKA SEQ SYSTEM v4.1 HuneX 2010」) 全文本提取。

源：PSP ISO9660 → PSP_GAME/USRDIR/DATA/GAMEDT.AFS（CRI AFS，8 成员）
  [0] 36,847,616 B  HFU2×409 —— キャラ別データ表（表情名/恋愛値/偏差値…）＝UI，非正文
  [1] 18,243,584 B  HFU2×121 —— 贴图包 ＋ ★単語解説（用語辞典）表
  [2]  1,357,824 B  HFU2×98  —— ★剧本（本作全部正文；块 = 场景脚本）
  [3] 12,120,064 B  HFU2×98  —— IKA SEQPACK（演出时间轴，0 条串）
  [4]-[7] 嵌套 AFS   —— SE / BGM / VOICE1-3（AT3）

文本命令（本作实测，白名单 4 条）：
  0x3E n=1  名前札（＠=姓 / ＄=名 / ★=地の文札）→ 丢（§0 不加说话人）
  0x3C n=3  台詞・独白                              → 收
  0x44 n=3  地の文                                  → 收
  0x41 n=4  選択肢（连排=同组；后 3 参数为写入值，丢） → 收
  0x5E n=1  メール件名（携帯メール画面の件名行）      → 收

★ 主人公：南 悠里（vndb v12934 / c28973，可改名）
  ＠→南（姓）、＄→悠里（名）
  依据：`＠探偵事務所`（南探偵事務所）／`＠＄です`（全名序＝姓+名）／`＄さん`（悠里さん）
        ／正文 0 处字面「悠里」、「南」仅作「南風」出现。

★ 块 0 是**開発用テストブロック**（携帯テスト ×5、１２３４…カウントアップ、
  記号テスト ㊤㊥㊦㊧㊨㈱㈲㈹㍾㍽、文字送り断片）。其实质内容与正文块重复
  （`タイミングよく着信`→block 97、`待ってたぜ怪盗`→block 12、`囮作戦`→block 38）
  ⇒ 整块剔除（见解析报告）。

控制码：`@n`＝框内软换行 → 合并；`@k…@w`＝着色（310 对）→ 去标记留字。
引号：原文仅 1 组 `「」`（台词内引用）＋138 组 `『』` ⇒ 引擎不上引号，无需补 `「`。

用語辞典：成员 1 内 `#\\tWORD_nnn` ＋ 2 条 `5C L <str> 00 00`（見出し語 / 解説）。
  23 条目（表存两份；WORD_006 クリケット 两版本，取首份并在报告记差异）
  ⇒ 末尾按 `【見出し語】解説文` 一行一条并入。

用法：python scripts/vitaminb6_extract.py <GAMEDT.AFS> <out.txt>
"""
import sys, os, re, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arcanafesta_extract import decode_hfu2

SCRIPT_MEMBER = 2
GLOSS_MEMBER = 1
SKIP_BLOCKS = {0}                     # 開発用テストブロック

NAME_CMDS = {0x3E}
TEXT_CMDS = {0x3C, 0x44, 0x5E}
CHOICE_CMD = 0x41
STR_CMDS = NAME_CMDS | TEXT_CMDS | {CHOICE_CMD}

NAMES = {'＠': '南', '＄': '悠里'}


def afs_member(data, idx):
    o, s = struct.unpack_from('<II', data, 8 + idx * 8)
    return data[o:o + s]


def iter_records(stream):
    """自定界走查：仅认 `26 cmd 24 n 5C L <text> 00 00`，产出 (cmd, txt)。"""
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


def clean(t):
    t = t.replace('@n', '')                        # 框内软换行 → 合并
    t = t.replace('@k', '').replace('@w', '')      # 着色标记
    for mac, rep in NAMES.items():
        t = t.replace(mac, rep)
    return t.replace('★', '').strip()


def parse_glossary(member):
    """`#\tWORD_nnn\0` + 2×(5C L str 00 00) → [(term, exp)]，同名去重保首份。"""
    raw = b''.join(decode_hfu2(member))
    out, seen = [], set()
    for m in re.finditer(rb'#\tWORD_\d{3}\x00', raw):
        p = m.end()                      # p → 0x5C（串种别）
        try:
            L = raw[p + 1]                   # L 含 0x5C 与 L 自身
            term = raw[p + 2:p + L - 2].decode('cp932')
            q = p + L
            L2 = raw[q + 1]
            exp = raw[q + 2:q + L2 - 2].decode('cp932')
        except (UnicodeDecodeError, IndexError):
            continue
        if term in seen:
            continue
        seen.add(term)
        out.append((term, exp.replace('@n', '').replace('@k', '').replace('@w', '').strip()))
    return out


def main():
    afs, out = sys.argv[1], sys.argv[2]
    data = open(afs, 'rb').read()
    assert data[:4] == b'AFS\x00', data[:4]

    blocks = decode_hfu2(afs_member(data, SCRIPT_MEMBER))
    lines, stat = [], {'block': 0, 'plate': 0, 'text': 0, 'choice': 0, 'mail': 0}
    for bi, blk in enumerate(blocks):
        if bi in SKIP_BLOCKS:
            continue
        stat['block'] += 1
        for cmd, txt in iter_records(blk):
            if cmd in NAME_CMDS:
                stat['plate'] += 1
                continue
            s = clean(txt)
            if not s:
                continue
            if cmd == CHOICE_CMD:
                stat['choice'] += 1
            elif cmd == 0x5E:
                stat['mail'] += 1
            else:
                stat['text'] += 1
            lines.append(s)

    gloss = parse_glossary(afs_member(data, GLOSS_MEMBER))
    for term, exp in gloss:
        lines.append('【%s】%s' % (term, exp))

    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('blocks', stat['block'], 'plates', stat['plate'], 'text', stat['text'],
          'choice', stat['choice'], 'mail', stat['mail'],
          'glossary', len(gloss), 'lines', len(lines))


if __name__ == '__main__':
    main()
