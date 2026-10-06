#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
クランク・イン (Crank In) — PSV / PCSG00941 / プチレーヴ (Puchireve)
全文本提取器
=====================================================================
引擎：自研「テキスト方式」ADV（脚本 = UTF-16LE 行式文本 + data/*.txt 指令表）

容器/管线：
  pkg2zip → psvpfsparser(PFS解密) → cmp.psarc 内 data/*.txt + script/*.txt

脚本規約（script/scriptN.txt）：
  · 1 行 = 1 个「步骤」。行为分三类：
      - 指令行：行文本恰好等于 data/{bg,bgm,se,change,chara,chart,flag}.txt 中登记的标签、
                或 scrlst.txt 的 label、或 `NNN:LABEL`
      - 话者名行：`姓　名`（含全角空格）或角色/职务词（係員/審査員/店員…）
      - 文本行：其余 → 游戏内显示的一段文本（对话「」/ 地の文 / 选项）
  · 一次点击 = 一个文本框 = 一行（本器输出）
  · `\`（反斜杠）= 框内软换行 → 合并
  · `[橘]` / `[文月]` = 主人公姓名占位符 → inline 为 橘 / 文月
  · 选项（选择肢）：位于分支 label 组（xxx_da/xxx_db/xxx_00…）之前的若干行

用法：
  python crankin_extract.py <解包后的 cmp.psarc 目录> <输出_全文本.txt> [输出_资料.txt]
"""
import os, re, sys, glob

PUNCT = set('「」『』（）()、。！？…―～♪ー' + chr(92) + '/’“”')
NAME_RE = re.compile(r'^[^\s]{1,7}\u3000[^\s]{0,7}$')

ROLE_WORDS = set('''係員 審査員 店員 園長 司会者 お母さん 先生 彼女 男性 女性 記者 スタッフ 団員 女優
アナウンサー 牧師 アナウンス 審査委員長 事務所社長 引ったくり犯 運転手 ドライバー 警官 救急隊員
ディレクター 助監督 ニュースキャスター 撮影スタッフ 売り子 時計店主 司書 秘書 店長 招待客
お父さん 時雨 時雨の母 柊の友達 神楽坂さん 周くん 聖くん 神楽坂の父 神楽坂の母 村雲の父
神楽坂の兄 教師 客 皆 全員'''.split())

# 端役/モブ（話者名）— 出现于剧本的固定话者
MOB_RE = re.compile(r'^[^\s]{0,12}(たち|員|客|スタッフ|生徒|学生|店員|記者|観客|通行人|友人|部員|園児|女優|教師|教諭|[Ａ-Ｇ]|[１２３])$')
# 指令变体（chara 变体 / 演出 / 系统）
CMD_EXTRA = set('''スチルス中 場面転換中遠 ガイダンス タイトル画面へ'''.split())


def is_cmd_variant(l):
    if l in CMD_EXTRA:
        return True
    if re.fullmatch(r'\d+', l):
        return True
    if '_' in l and not has_punct(l):
        return True
    if not has_punct(l) and re.search(r'(スチル|場面転換|フェード|bgmout|bgmin)', l):
        return True
    return False

HERO_SURNAME = '橘'
HERO_GIVEN = '文月'


def rd(p):
    d = open(p, 'rb').read()
    if d[:2] == b'\xff\xfe':
        return d[2:].decode('utf-16-le', 'replace')
    return d.decode('utf-16-le', 'replace')


def rd_swap(p):
    return open(p, 'rb').read().decode('utf-16-be', 'replace')


def load_cmds(root):
    cmds = set()

    def add(f, col, sw=False):
        if not os.path.exists(f):
            return
        s = rd_swap(f) if sw else rd(f)
        for l in s.replace('\r\n', '\n').split('\n'):
            if not l:
                continue
            p = l.split(',')
            if len(p) > col:
                cmds.add(p[col])

    d = os.path.join(root, 'data')
    add(os.path.join(d, 'bg.txt'), 0)
    add(os.path.join(d, 'bgm.txt'), 0)
    add(os.path.join(d, 'se.txt'), 0)
    add(os.path.join(d, 'change.txt'), 0)
    add(os.path.join(d, 'chara.txt'), 1)
    add(os.path.join(d, 'flag.txt'), 0, True)
    add(os.path.join(d, 'chart.txt'), 0)
    s = rd(os.path.join(d, 'scrlst.txt'))
    for l in s.split('\r\n'):
        p = l.split(',')
        if p and p[0]:
            cmds.add(p[0])
    for f in glob.glob(os.path.join(root, 'script', '*_l.txt')):
        for l in rd(f).replace('\r\n', '\n').split('\n'):
            if ':' in l:
                cmds.add(l.split(':', 1)[1].strip())
    return cmds


def has_punct(l):
    return any(c in PUNCT for c in l)


def is_name(l):
    if l in ROLE_WORDS or l in CMD_EXTRA:
        return True
    if re.fullmatch(r'[?？]+', l):
        return True
    if has_punct(l):
        return False
    if MOB_RE.match(l):
        return True
    if '\u3000' in l and len(l) <= 15:
        return True
    return False


def is_cue(l):
    # 効果音の説明行（例：歩いて行く足音 / 拍手の音 / 近づいてくる二人の足音）
    if has_punct(l):
        return False
    if l.endswith('音') and 2 <= len(l) <= 20:
        return True
    return False


def is_misc_cmd(l):
    if 'bgmout(' in l or 'bgmin(' in l or '(' in l and ')' in l and not has_punct(l):
        return True
    return False


def classify(l, cmds):
    if not l.strip():
        return 'blank'
    if l in cmds:
        return 'cmd'
    if re.match(r'^\d+:', l):
        return 'label'
    if is_name(l):
        return 'name'
    if is_cmd_variant(l):
        return 'misc'
    if is_cue(l):
        return 'cue'
    if is_misc_cmd(l):
        return 'misc'
    return 'text'


def clean(t):
    t = t.replace('\\', '')          # 框内软换行 → 合并
    t = t.replace('[橘]', HERO_SURNAME).replace('[文月]', HERO_GIVEN)
    return t


def main(root, out_text, out_data=None):
    cmds = load_cmds(root)
    scr = os.path.join(root, 'data', 'scrlst.txt')
    rows = [l.split(',') for l in rd(scr).split('\r\n') if l]
    lines = []
    ntext = 0
    for r in rows:
        if len(r) < 4 or not r[1]:
            continue
        name = r[1]
        if name in ('script', 'script0'):
            continue
        p = os.path.join(root, 'script', name + '.txt')
        if not os.path.exists(p):
            continue
        for l in rd(p).split('\n'):
            k = classify(l, cmds)
            if k == 'text':
                t = clean(l)
                if t.strip():
                    lines.append(t)
                    ntext += 1
    os.makedirs(os.path.dirname(out_text), exist_ok=True)
    with open(out_text, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'text lines = {ntext}  -> {out_text}')
    return lines


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
