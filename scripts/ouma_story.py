#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《逢魔が刻 ～かくりよの縁～》本編 ADV シナリオ抽出 (NML スクリプト)

SoundSysMSG.dat = 943 個の NML スクリプトブロック (scene, id 10001–95008)。
  レコード = 0xFF <u8 全長> <operand...>
  テキスト = 0x00 以外の連続バイト。**cp932 の各バイトを 0xFF で XOR** したもの
            (= 本来のバイトの bitwise NOT)。
  オペコード (operand 先頭 u16):
    0x0003 … テキストボックス開始 (= 1 クリック)。出現 28,499 回 (story.dat と一致)
    0x00d5 … 主人公名の差し込み。flag(末尾 u16) 0x0000 = 姓「榊」 / 0x0001 = 名「水緒」
    0x00cc … ボックス内の表示行
用法: python ouma_story.py <SoundSysMSG.dat> <out.txt>
"""
import re
import struct
import sys

SURNAME = '榊'      # 既定姓
GIVEN = '水緒'      # 既定名
MARK = '\u8740\u8741\u8745'          # ㊤ ㊦ ㊥ (引擎ルビ/名前マーカー)
PUA = re.compile(r'[\uf8f0-\uf8ff]')
CTRL = re.compile(r'[\x00-\x1f]')
MARKERS = set('\u32a4\u32a5\u32a6'          # ㊤ ㊥ ㊦ (引擎ルビ/名前マーカー)
              '\uf8f0\uf8f1\uf8f2\uf8f3\uf8f4\uf8f5\uf8f6\uf8f7'
              '\uf8f8\uf8f9\uf8fa\uf8fb\uf8fc\uf8fd\uf8fe\uf8ff'
              '\u8740\u8741\u8742\u8743\u8744\u8745\u8746\u8747'
              '\u8748\u8749\u874a\u874b\u874c\u874d\u874e\u874f')


def decode(b):
    return bytes(v ^ 0xFF for v in b).decode('cp932', 'replace')


def tokenize(d, off, lim):
    out = []
    p = off
    while p < lim:
        if d[p] == 0xFF and p + 1 < lim:
            L = d[p + 1]
            if 2 <= L <= 200 and p + L <= lim:
                out.append(('C', d[p + 2:p + L]))
                p += L
                continue
            p += 1
            continue
        if d[p] == 0x00:
            p += 1
            continue
        s = p
        while p < lim and d[p] != 0xFF:
            p += 1
        out.append(('T', d[s:p]))
    return out


DASH = '\u2015'          # ― (引擎字体槽 ㊤/㊥/㊦ 实际显示的字符)


def clean(s):
    # 字体替换槽：㊤(U+32A4)/㊥(U+32A5)/㊦(U+32A6) 运行时显示为长破折号
    s = s.replace('\u32a4', DASH).replace('\u32a5', DASH).replace('\u32a6', DASH)
    s = ''.join(c for c in s if c not in MARKERS)
    s = PUA.sub('', s)
    s = CTRL.sub('', s)
    return s.replace('\u3000', ' ')


def main():
    src, dst = sys.argv[1], sys.argv[2]
    d = open(src, 'rb').read()
    ds, cnt = struct.unpack_from('<II', d, 0)
    ents = sorted([struct.unpack_from('<II', d, 8 + i * 8) for i in range(cnt)],
                  key=lambda x: x[1])
    lims = [e[1] for e in ents] + [len(d)]

    lines = []
    for k, (iid, off) in enumerate(ents):
        ts = tokenize(d, off, lims[k + 1])
        box = []
        started = False
        nameflags = []

        def flush_name():
            # 0x00d5 命令：flag 0x0000 = 姓(榊) / 0x0001 = 名(水緒)。按出现顺序拼接，
            # 故「[0][1]」→ 榊水緒（与原文一致）。
            for fl in nameflags:
                box.append(SURNAME if fl == 0x0000 else GIVEN)
            del nameflags[:]

        for t in ts:
            if t[0] == 'C':
                if len(t[1]) < 2:
                    continue
                op = struct.unpack_from('<H', t[1])[0]
                if op == 0x0003:
                    flush_name()
                    if started:
                        lines.append(''.join(box))
                    box = []
                    started = True
                elif op == 0x00d5 and started and len(t[1]) >= 8:
                    nameflags.append(struct.unpack_from('<H', t[1], 6)[0])
                else:
                    flush_name()
                continue
            if started:
                flush_name()
                box.append(decode(t[1]))
        flush_name()
        if started:
            lines.append(''.join(box))

    out = []
    for s in lines:
        s = clean(s)
        if s.strip():
            out.append(s)
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(out) + '\n')
    print('textboxes=%d  non-empty lines=%d  ->  %s' % (len(lines), len(out), dst))


if __name__ == '__main__':
    main()
