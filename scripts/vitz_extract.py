#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VitaminZ (PSP, ULJS00240, HuneX「IKA SEQ SYSTEM v3.4 HuneX 2009」) 全文本提取。

源：CHD v5 → scripts/chd_to_iso.js → ISO9660 → PSP_GAME/USRDIR/data/GAMEDT.afs（CRI AFS，7 成员）
  [0] 56 MB HFU2×835 —— 场景/立绘包（无文本命令）
  [1] 17 MB HFU2×104 —— 系统脚本包：★用語辞典(blk2)＋★授業クイズ(blk3)＋★おみくじ(blk87)＋名簿(blk63=UI，剔)
  [2]  4 MB HFU2×337 —— ★剧本（块 0＝開発テスト）
  [3] 35 MB HFU2×362 —— IKA SEQPACK（演出时间轴，无串）
  [4]-[6] AFS        —— SE / BGM / VOICE

文本命令（本作实测）：
  0x3E n=1  名前札（`＠`＝名（真奈美）/ `☆`＝地の文札）→ 丢（§0 不加说话人）
  0x3C n=3  台詞・独白                                  → 收  69,3xx
  0x44 n=3  地の文                                      → 收   2,443
  0x41 n=3  選択肢                                      → 收     522
  0xBE n=2  選択肢（第二载体，短句对）                   → 收      84

★★ 主人公宏：`＄`＝姓（北森）／`＠`＝名（真奈美）—— 与前作 Graduation（＠姓/＄名）**相反**
  依据 ① 自介句 `私の名前は、＄＠。` / `＄＠と申します`（全名序＝姓+名）
       ② `＄先生` 445（学生称「北森先生」）/ `＠せんせい` 76（亲近者称其名）
       ③ `＄さんとか、＠さんとか呼んで欲しいな`
       ④ ELF EBOOT.dec @0x1dd760 名字池 `＠`(0x8197) ＋ `真奈美` ＋ `北森` ＋ `☆`

末尾并入（标签数据表载体 `23 <L> <LABEL> <tag>` ＋ 后续 `5C L` 串）：
  用語辞典   member1 blk2   `WORD_xx_nnn`                  見出し ＋ 解説 → 【見出し】解説
  授業クイズ member1 blk3   `<CHAR>_{0,1}_Q_nnn`（10 人×2）  設問 ＋ 選択肢×4
  おみくじ   member1 blk87  `FORTUNEWORD__` / `WORD___nnn`  占い結果 1 串

控制码：`@n`＝框内软换行 → 合并；`@k…@w`＝着色 → 去标记留字；`☆`＝地の文札残留 → 删。

用法：python scripts/vitz_extract.py <GAMEDT.AFS> <out.txt> [--no-quiz] [--no-omikuji] [--no-gloss]
"""
import sys, os, struct, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arcanafesta_extract import decode_hfu2

SCRIPT_MEMBER = 2
SYS_MEMBER = 1
SKIP_BLOCKS = {0}                      # 块 0＝開発テスト（選択肢Ａ/Ｂ テスト 10 条）
NAME_CMDS = {0x3E}
TEXT_CMDS = {0x3C, 0x44}
CHOICE_CMDS = {0x41, 0xBE}
STR_CMDS = NAME_CMDS | TEXT_CMDS | CHOICE_CMDS
MACROS = {'＄': '北森', '＠': '真奈美'}

# 标签记录 `23 <L> <ASCII label> <tag>`；L ＝ len(label) + 1
LABEL_RE = re.compile(rb'\x23(?P<L>.)(?P<lab>[A-Z][A-Z0-9_]{2,24})')
QUIZ_RE = re.compile(r'^[A-Z]+_[01]?_+Q_\d+$')
QUIZ_RE2 = re.compile(r'^[A-Z]+_[01]_Q_\d+$')


def afs_member(data, idx):
    o, s = struct.unpack_from('<II', data, 8 + idx * 8)
    return data[o:o + s]


def iter_records(stream, bad=None):
    """自定界走查：`26 <cmd> 24 <n> 5C <L> …` ＋ L 校验 ＋ 双 NUL 收尾。"""
    i, N = 0, len(stream) - 4
    while i < N:
        if stream[i] == 0x26 and stream[i + 2] == 0x24 and stream[i + 4] == 0x5C:
            cmd = stream[i + 1]
            if cmd in STR_CMDS:
                L = stream[i + 5]
                if 4 <= L <= 1200 and i + 4 + L <= len(stream) \
                        and stream[i + 4 + L - 2] == 0 and stream[i + 4 + L - 1] == 0:
                    try:
                        txt = stream[i + 6:i + 4 + L - 2].decode('cp932')
                    except UnicodeDecodeError:
                        if bad is not None:
                            bad.append((cmd, i))
                        i += 1
                        continue
                    yield cmd, txt
                    i += 4 + L
                    continue
        i += 1


def clean(t):
    t = t.replace('@n', '')
    t = t.replace('@k', '').replace('@w', '')
    for mac, rep in MACROS.items():
        t = t.replace(mac, rep)
    return t.replace('☆', '').strip()


def strings_in(seg):
    out, i, N = [], 0, len(seg) - 4
    while i < N:
        if seg[i] == 0x5C:
            L = seg[i + 1]
            if 4 <= L <= 1200 and i + L <= len(seg) \
                    and seg[i + L - 2] == 0 and seg[i + L - 1] == 0:
                try:
                    out.append(seg[i + 2:i + L - 2].decode('cp932'))
                except UnicodeDecodeError:
                    pass
                i += L
                continue
        i += 1
    return out


def labels(block):
    out = []
    for m in LABEL_RE.finditer(block):
        lab = m.group('lab').decode()
        if ord(m.group('L')) == len(lab) + 1:
            out.append((m.start(), m.end(), lab))
    return out


def entries(block, accept):
    """按标签切段：产出 (label, [串…])"""
    ls = [x for x in labels(block) if accept(x[2])]
    for k, (st, en, lab) in enumerate(ls):
        end = ls[k + 1][0] if k + 1 < len(ls) else len(block)
        yield lab, strings_in(block[en:end])


def main():
    argv = sys.argv[1:]
    flags = {a for a in argv if a.startswith('--')}
    args = [a for a in argv if not a.startswith('--')]
    afs, out = args[0], args[1]
    data = open(afs, 'rb').read()
    assert data[:4] == b'AFS\x00', data[:4]

    blocks = decode_hfu2(afs_member(data, SCRIPT_MEMBER))
    lines = []
    stat = {'block': 0, 'plate': 0, 'text': 0, 'choice': 0, 'empty': 0, 'bad': 0}
    bad = []
    for bi, blk in enumerate(blocks):
        if bi in SKIP_BLOCKS:
            continue
        stat['block'] += 1
        for cmd, txt in iter_records(blk, bad):
            if cmd in NAME_CMDS:
                stat['plate'] += 1
                continue
            s = clean(txt)
            if not s:
                stat['empty'] += 1
                continue
            if cmd in TEXT_CMDS:
                stat['text'] += 1
            else:
                stat['choice'] += 1
            lines.append(s)
    stat['bad'] = len(bad)

    sysb = decode_hfu2(afs_member(data, SYS_MEMBER))
    n_gloss = n_quiz = n_omi = 0

    if '--no-gloss' not in flags:
        seen = set()
        for lab, ss in entries(sysb[2], lambda l: l.startswith('WORD_')):
            if len(ss) < 2:
                continue
            head, exp = clean(ss[0]), clean(ss[1])
            if not head or not exp or (head, exp) in seen:
                continue
            seen.add((head, exp))
            lines.append('【%s】%s' % (head, exp))
            n_gloss += 1

    if '--no-quiz' not in flags:
        for lab, ss in entries(sysb[3], lambda l: bool(QUIZ_RE.match(l) or QUIZ_RE2.match(l))):
            if len(ss) < 5:
                continue
            for s in ss:
                s = clean(s)
                if s:
                    lines.append(s)
                    n_quiz += 1

    if '--no-omikuji' not in flags:
        for lab, ss in entries(sysb[87], lambda l: l.startswith('WORD_') or l.startswith('FORTUNE')):
            for s in ss:
                s = clean(s)
                if s:
                    lines.append(s)
                    n_omi += 1

    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('blocks', stat['block'], 'plates', stat['plate'], 'text', stat['text'],
          'choice', stat['choice'], 'empty', stat['empty'], 'bad', stat['bad'],
          '| gloss', n_gloss, 'quiz', n_quiz, 'omikuji', n_omi, '| lines', len(lines))


if __name__ == '__main__':
    main()
