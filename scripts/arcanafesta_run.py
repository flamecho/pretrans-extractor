#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""アルカナ・ファミリア フェスタ・レガーロ! (PSP) 成品生成。

输入：ISO 路径（PSP_GAME/USRDIR/DATA/GAMEDT.AFS）
输出：提取结果/アルカナファミリア_フェスタレガーロ_全文本.txt
  ① 正文＋选项（来源 = GAMEDT.AFS[2] = SCRIPT，IKA SEQ SYSTEM v4.2）
  ② 末尾并入 ワード辞典（用語辞典，来源 = GAMEDT.AFS[1] = GAMEDT，固定记录表）
"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arcanafesta_extract import (parse_iso_afs, parse_afs_members, decode_hfu2,
                                 iter_str_records, extract_lines)

DICT_S = 0xf0          # 辞典记录 stride
DICT_TERM_OFF = 12     # 记录内 見出し語 偏移
DICT_ANCHOR = 0x27b050  # 表首（id 0 = アクアパッツァ）


def extract_word_dict(mem1):
    """从 GAMEDT 解压流里提取 ワード辞典（固定 0xf0 记录：見出し語 + 解説）。"""
    b = mem1
    out = []

    def rec(o):
        if o < 0 or o + DICT_S > len(b):
            return None
        t0 = o + DICT_TERM_OFF
        z = b.find(b'\x00', t0, o + DICT_S)
        if z < 0:
            return None
        term = b[t0:z]
        if not (2 <= len(term) <= 30):
            return None
        try:
            term = term.decode('cp932')
        except UnicodeDecodeError:
            return None
        expl = b[z:o + DICT_S]
        try:
            expl = expl.decode('cp932')
        except UnicodeDecodeError:
            return None
        expl = expl.replace('\x00', '')
        if sum(1 for c in expl if '\u3040' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff') < 4:
            return None
        return term, expl

    # 向前找表首
    start = DICT_ANCHOR
    while rec(start - DICT_S):
        start -= DICT_S
    k = 0
    while True:
        r = rec(start + k * DICT_S)
        if not r:
            break
        out.append(r)
        k += 1
    return out


def main():
    iso = sys.argv[1]
    outpath = sys.argv[2] if len(sys.argv) > 2 else '提取结果/アルカナファミリア_フェスタレガーロ_全文本.txt'
    afs = parse_iso_afs(iso)
    mems = parse_afs_members(afs)

    def hfu2_blob(i):
        off, size = mems[i]
        return b''.join(decode_hfu2(afs[off:off + size]))

    # ① 正文＋选项
    script = hfu2_blob(2)
    lines, stats = extract_lines(script)
    print('script lines=%d stats=%s' % (len(lines), {hex(k) if isinstance(k, int) else k: v for k, v in stats.items()}))

    # ② 用語辞典
    gamedt = hfu2_blob(1)
    dic = extract_word_dict(gamedt)
    print('word dict entries=%d' % len(dic))

    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    with open(outpath, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
        if dic:
            for term, expl in dic:
                f.write('【%s】%s\n' % (term, expl))
    print('wrote %s' % outpath)


if __name__ == '__main__':
    main()
