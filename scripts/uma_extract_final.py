# -*- coding: utf-8 -*-
"""冬園サクリフィス [NS-JP] UTXT 文本提取（代码级切分：仅用 0x00 换行码，无括号启发式）

容器 UTXT (16B 头):
    +0x00 magic 'UTXT'
    +0x04 u32 version = 1
    +0x08 u32 常量 0x0037DB21（三份 .bytes 共有，非长度/偏移）
    +0x0C u32 字符流绝对偏移          <- 两份文件互相印证
字符流:
    0x00                -> '\n'（引擎换行码；其后紧跟的 U+3000 由
                           RemoveZenkakuSpaceAfterNewLine 剥掉）
    0x01..0x7F          -> chartable[b-1]
    0x81..0xBA + trail  -> chartable[trail + 128*(b-0x81) + 127]
行内标记:
    $...$  辞書語（引擎用以致辞书链接，剥壳）
    %      主人公名占位
"""
import sys
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

CHART = os.path.join(VNTRANS_HOME, '_w_wgs/chartable.bin')
ROOT = r'<本地路径>'
OUT = os.path.join(VNTRANS_HOME, '提取结果/[NS-JP]冬園サクリフィス.txt')
HEROINE = 'レティシア'

T = open(CHART, 'rb').read().decode('utf-8')


def load(fn):
    d = open(ROOT + fn, 'rb').read()
    assert d[:4] == b'UTXT', 'not UTXT: %r' % d[:4]
    off = int.from_bytes(d[12:16], 'little')
    chars, i = [], off
    while i < len(d):
        b = d[i]
        if b == 0:
            chars.append('\n'); i += 1
        elif b < 0x80:
            chars.append(T[b - 1]); i += 1
        else:
            chars.append(T[d[i + 1] + 128 * (b - 0x81) + 127]); i += 2
    return ''.join(chars)


def build(talk):
    lines = []
    for row in talk.split('\n'):
        row = row.lstrip('\u3000')          # 引擎行为：剥掉换行后的全角空格
        if not row.strip():
            continue
        row = row.replace('$', '').replace('%', HEROINE)
        lines.append(row)
    return lines


if __name__ == '__main__':
    talk = load('uma_talk_2.bytes')     # 引擎自带的“已剥控制符”文本
    text = load('uma_text_2.bytes')     # 原文含内联 NONE/REGIS/001_004_00/TC8001 等
    lines = build(talk)
    print('talk chars %d / text chars %d / lines %d' % (len(talk), len(text), len(lines)))
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('written', OUT)
