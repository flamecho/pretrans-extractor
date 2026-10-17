#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""ニル・アドミラリの天秤 色ドリ撫子 (Switch) —— 全文本提取器

作品: Otomate / Idea Factory, NS 合集（『帝都幻惑綺譚』＋『クロユリ炎陽譚』）
引擎: Idea Factory **STCM2L**（Switch / **CP932**）—— 与「猛獣」「BWS」「GHP」同族但**记录框架自成一型**。

链路:
  XCI → hactool -t nca --romfsdir → RomFS/CONTENTS/{GAME01,GAME02}.cpk（CRI CPK）
  → script/NNNN（STCM2L）
  GAME01 = 帝都幻惑綺譚（本体） / GAME02 = クロユリ炎陽譚（FD）

脚本格式（本作实证）:
  * 文件头 `STCM2L <date>\0`；`CODE_START_\0` 之后为节点区。
  * 节点通用布局: `[KIND][k][size][p1][2.0][2.0][p2...][0][L/4][1][L][cp932 text][pad]`
    - k=1 头 40B（2 个指针组）/ k=2 头 52B（3 组）/ k=3 头 64B（4 组）…  头长 = 28+12k, L 字段 = off+24+12k
    - L = align4(byte_len + 1)；`1` 字段 = L 字段前一格，`0` 字段再前一格（强签名）
  * 文本载体（本作全库统计）:
    - **k=1 KIND=0x4BA = 正文/台词**（收）           - **k=1 KIND=0x4BC = 話者名**（丢）
    - **k=3 KIND=0x4CF = 选项**（收，一行一条）      - k=2 KIND=0x4C0 = シーン/回想タイトル 131 项（本作＝画廊元数据 ⇒ 剔）
    - k=1 KIND=0x3C = `処理開始` 调试日志（剔）      - 其余 = 资源名/flag/switch（剔）
  * **一次点击（＝一个文本框）＝ [可选名札] ＋ 1〜n 个「地址连续」的正文节点**，
    由 **`[0][0x4BB][0][0x10]`（16B 终止记录）** 分隔。框内多节点 = 软换行 ⇒ **直接拼接成一行**。

用法:
  python scripts/niladmirari_extract.py <script目录[,script目录...]> <out.txt> [--name ツグミ]
"""
import os
import re
import sys
import glob
import struct
import collections

A4 = lambda n: (n + 3) & ~3
BODY, NAMEK, TITLEK, OPTK, DEBUGK = 0x4BA, 0x4BC, 0x4C0, 0x4CF, 0x3C
TERM = bytes.fromhex('00000000bb0400000000000010000000')   # [0][0x4BB][0][0x10]
BOX_GAP = 8            # 同框两行之间允许的字节间隙
NAME_MACRO = {1: 'ツグミ'}          # 主角名（#Name[1]）＝久世 ツグミ（vndb v18163，Nameable）

RE_RUBY = re.compile(r'#Ruby\[([^,\]]+),[^\]]*\]')      # ルビ: 保留基底语
RE_NAME = re.compile(r'#Name\[(\d)\]')
RE_STYLE = re.compile(r'#[A-Za-z][A-Za-z0-9_]*\[[^\]]*\]')
JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')

# ── 原文笔误 整行定值表（仅修引号/括号，不改内容；逐条已在源字节核实）───────────────
# 「A」␣B」 型 ⇒ 中间那个 」 是衍字（去掉）；「 未闭合 ⇒ 行尾补 」；『…」 ⇒ 作 』；
# 半角 ( / ) 与全角 （ / ） 混用 ⇒ 归一为全角（§0 允：笔误用整行定值表修）。
FIXES = {
    '「この手を……離しなさい！！':
        '「この手を……離しなさい！！」',
    '「……良かった、この間の傷は」\u3000もう治りかけていますね」':
        '「……良かった、この間の傷は\u3000もう治りかけていますね」',
    '「……何だか、今日は郵便が多いみたいですね」\u3000私も配達のお手伝いをします」':
        '「……何だか、今日は郵便が多いみたいですね\u3000私も配達のお手伝いをします」',
    '「紫鶴さん！\u3000紫鶴さん、起きてますか！？」\u3000もう寝てしまいましたか？」':
        '「紫鶴さん！\u3000紫鶴さん、起きてますか！？\u3000もう寝てしまいましたか？」',
    '「……お願いします、協力させて下さい！':
        '「……お願いします、協力させて下さい！」',
    '『死ね、死ね死ね、死ね……───！！」':
        '『死ね、死ね死ね、死ね……───！！』',
    '「でも現にああして来ているわけでしょう？\u3000そのうち杙梛さんまで巻き込まれたらどうする」\u3000つもりですか」':
        '「でも現にああして来ているわけでしょう？\u3000そのうち杙梛さんまで巻き込まれたらどうする\u3000つもりですか」',
    '「ええ、全く。これでも結構頑丈なんです」\u3000貴女は散歩？」':
        '「ええ、全く。これでも結構頑丈なんです\u3000貴女は散歩？」',
    '(……こんな時は、流し台でも磨こう）':
        '（……こんな時は、流し台でも磨こう）',
    '(……みんなには迷惑を掛けることになって\u3000しまうけれど、でもいつか……）':
        '（……みんなには迷惑を掛けることになって\u3000しまうけれど、でもいつか……）',
    '(何があっても忘れませんとも）':
        '（何があっても忘れませんとも）',
    '（そう言えば昌吾も、絶対に発売日に買うと\u3000言っていたわね )':
        '（そう言えば昌吾も、絶対に発売日に買うと\u3000言っていたわね）',
}


def scan(d):
    """返回 [(off, KIND, k, text)]，按字节序。文本载体之外的 KIND 也一并返回（供框判定）。"""
    n = len(d); out = []; i = 0
    while i + 40 <= n:
        k = struct.unpack_from('<I', d, i + 4)[0]
        if 1 <= k <= 6:
            iL = i + 24 + 12 * k
            if iL + 4 <= n:
                L = struct.unpack_from('<I', d, iL)[0]
                if (4 <= L <= 0x20000 and L % 4 == 0 and iL + 4 + L <= n
                        and struct.unpack_from('<I', d, iL - 8)[0] == L // 4
                        and struct.unpack_from('<I', d, iL - 4)[0] == 1
                        and struct.unpack_from('<I', d, iL - 12)[0] == 0
                        and struct.unpack_from('<I', d, i + 16)[0] == 0x40000000
                        and struct.unpack_from('<I', d, i + 20)[0] == 0x40000000):
                    txt = d[iL + 4:iL + 4 + L].rstrip(b'\x00').decode('cp932', 'replace')
                    out.append((i, struct.unpack_from('<I', d, i)[0], k, iL + 4 + L, txt))
                    i = iL + 4 + L
                    continue
        i += 1
    return out


def transform(txt, name):
    txt = RE_RUBY.sub(lambda m: m.group(1), txt)
    txt = RE_NAME.sub(lambda m: name.get(int(m.group(1)), m.group(0)), txt)
    txt = RE_STYLE.sub('', txt)
    return txt.replace('\\n', '')          # 译注用转义换行（资源串残留）


def build_lines(d, name):
    nodes = scan(d)                        # (off, KIND, k, end, text)
    bodies = [nd for nd in nodes if nd[1] == BODY]
    bset = {nd[0] for nd in bodies}
    # 框 = 地址连续的正文节点串（间隙 ≤ BOX_GAP；名札不计入但允许夹在中间）
    lines = []
    i = 0
    while i < len(bodies):
        grp = [bodies[i]]
        j = i + 1
        while j < len(bodies):
            gap = bodies[j][0] - grp[-1][3]
            if 0 <= gap <= BOX_GAP:
                grp.append(bodies[j]); j += 1
            else:
                break
        s = transform(''.join(g[4] for g in grp), name).strip()
        if s:
            lines.append((grp[0][0], s))
        i = j
    # 选项：每个 0x4CF 节点单独一行
    for nd in nodes:
        if nd[1] == OPTK:
            s = transform(nd[4], name).strip()
            if s:
                lines.append((nd[0], s))
    lines.sort()
    # 排除：调试日志 / 非日文资源串 + 原文笔误定值修正
    out = []
    for off, s in lines:
        if s == '処理開始':
            continue
        if not JP.search(s) and not re.search(r'[「」『』。、！？…—―]', s):
            continue
        out.append(FIXES.get(s, s))
    return out


def main():
    if len(sys.argv) < 3:
        print(__doc__); return 1
    srcs = sys.argv[1].split(',')
    out = sys.argv[2]
    name = dict(NAME_MACRO)
    if '--name' in sys.argv:
        name[1] = sys.argv[sys.argv.index('--name') + 1]
    files = []
    for src in srcs:
        files.extend(sorted(glob.glob(os.path.join(src, '*')), key=lambda p: int(os.path.basename(p))))
    all_lines = []; nfiles = 0
    for f in files:
        d = open(f, 'rb').read()
        if d[:6] != b'STCM2L':
            continue
        nfiles += 1
        all_lines.extend(build_lines(d, name))
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as fh:
        for ln in all_lines:
            fh.write(ln + '\n')
    print('files=%d lines=%d -> %s' % (nfiles, len(all_lines), out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
