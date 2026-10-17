#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
5人の恋プリンス ~ヒミツの契約結婚~ (PSV, PCSG00590) 文本提取

引擎：自定义 ADV（文本型脚本 .TAT；<TAG> 指令 + [LABEL] + 正文行；<KW><WinClear> = 一次点击）
链路：NoNpDrm zip -> psvpfsparser(-z games.json[PCSG00590]) -> 解密后 script_tat/*.TAT 为 UTF-8-BOM 明文

用法:
    python scripts/prince5_extract.py [--src <解密后 script_tat 目录>] [--out <输出txt>]
"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import sys
import argparse

DEFAULT_SRC = os.path.join(VNTRANS_HOME, "_src_prince5/dec/script_tat")
DEFAULT_OUT = os.path.join(VNTRANS_HOME, "提取结果/[PSV-JP]5人の恋プリンス ~ヒミツの契約結婚~_全文本.txt")

# 主角可改名：游戏内「あなたの苗字を入力してください / 下の名前を入力してください」，
# 输入框无默认值（eboot 内无默认串），故取一个不与任何角色冲突的占位名，便于译文统一查找替换。
NAME_FIRST = "ひなた"
NAME_FAMILY = "小野寺"

TAG_RE = re.compile(r'<[^>]*>')
CTRL_RE = re.compile(r'#[SC][0-9A-Za-z]')          # #S5/#SC=文字送り速度, #C0-9=色（非表示）
SLTADD_RE = re.compile(r'^<SltAdd\s+(\d+)\s*,\s*(.*?)\s*,\s*(.*?)>$')

# 源脚本定值修（原文笔误，逐条记录在报告里）
FIX_LINES = {
    # SCR_NOZUMU_end_a.TAT 收尾台词缺右引号（同句在其它线路都有 」）
    '「ふふっ。私たちもノゾムさんが帰ってくるのを、首を長くして待ってましたよ。':
        '「ふふっ。私たちもノゾムさんが帰ってくるのを、首を長くして待ってましたよ。」',
    # 结局回顾处 『…」』 右引号笔误（应为 』）
    '『５人の兄弟の中から、１人を選んで結婚してください」』':
        '『５人の兄弟の中から、１人を選んで結婚してください』',
}


def read_text(path):
    raw = open(path, 'rb').read()
    return raw.decode('utf-8-sig', errors='strict')


def clean(piece):
    piece = TAG_RE.sub('', piece)
    piece = CTRL_RE.sub('', piece)
    piece = piece.replace('{firstname}', NAME_FIRST).replace('{familyname}', NAME_FAMILY)
    # 原文半角引号/括号笔误归一（SYOU 线整体把 」 写成 ｣）
    piece = piece.replace('\uff62', '\u300c').replace('\uff63', '\u300d')
    piece = piece.replace('(', '\uff08').replace(')', '\uff09')
    return piece.strip()


def emit(boxes, buf):
    t = ''.join(buf)
    boxes.append(FIX_LINES.get(t, t))


def parse_file(path, boxes, choices):
    """按「积攒物理行 -> 遇 <KW> 收框」成行；顺带收集选项。"""
    buf = []
    for line in read_text(path).split('\n'):
        s = line.strip()
        if not s:
            continue
        if s.startswith('//'):
            continue
        if s.startswith('['):
            continue
        if s.startswith('【') and s.endswith('】'):
            # 独立名札行：丢弃（不加说话人前缀）
            continue
        if s.startswith('<'):
            m = SLTADD_RE.match(s)
            if m:
                txt = clean(m.group(3))
                if txt:
                    if buf:
                        emit(boxes, buf)             # 选项出现前先收束当前文本框
                        buf = []
                    boxes.append(txt)                # 选项按出现顺序就地落行
                    choices.append(txt)
            if '<KW>' in s:
                if buf:
                    emit(boxes, buf)
                    buf = []
            continue
        if '//《' in s or '*:' in s or '》' in s:
            # 源脚本自带的破损指令行（tag 缺 '>' 被截断，残片/自动注释）
            continue
        has_kw = '<KW>' in s
        head = s.split('<KW>')[0]
        t = clean(head)
        if t:
            buf.append(t)
        if has_kw:
            if buf:
                emit(boxes, buf)
                buf = []
    if buf:
        emit(boxes, buf)


def route_dir_order():
    return ['01_HIBIKI', '02_TAKERU', '03_NOZOMU', '04_KAEDE', '05_SYOU', '06_MAKI']


def script_order(src):
    """PRO -> 每条线 01..29（_h 紧跟本篇） -> end_a..d；排除 _m(回想副本)/CERO/000_test/misc。"""
    files = []

    def add(p):
        if os.path.isfile(p):
            files.append(p)

    add(os.path.join(src, '00_PRO', 'SCR_PRO_A.TAT'))
    add(os.path.join(src, '00_PRO', 'SCR_PRO_B.TAT'))
    for d in route_dir_order():
        base = os.path.join(src, d)
        if not os.path.isdir(base):
            continue
        for i in range(1, 40):
            add(os.path.join(base, 'SCR_%s_%02d.TAT' % (d.split('_', 1)[1], i)))
            add(os.path.join(base, 'SCR_%s_%02d_h.TAT' % (d.split('_', 1)[1], i)))
        for e in 'abcd':
            add(os.path.join(base, 'SCR_%s_end_%s.TAT' % (d.split('_', 1)[1], e)))
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=DEFAULT_SRC)
    ap.add_argument('--out', default=DEFAULT_OUT)
    args = ap.parse_args()

    files = script_order(args.src)
    boxes, choices, stat = [], [], []
    for f in files:
        b, c = [], []
        parse_file(f, b, c)
        boxes.extend(b)
        choices.extend(c)
        stat.append((os.path.relpath(f, args.src), len(b), len(c)))

    out = boxes
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w', encoding='utf-8-sig', newline='\n') as fp:
        fp.write('\n'.join(out) + '\n')

    print('files %d  boxes %d  choices %d  lines %d' % (len(files), len(boxes), len(choices), len(out)))
    for r, nb, nc in stat:
        print('  %-34s %5d %3d' % (r, nb, nc))
    print('-> %s' % args.out)


if __name__ == '__main__':
    main()
