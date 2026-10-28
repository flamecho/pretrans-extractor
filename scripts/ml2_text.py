#!/usr/bin/env python3
"""ml2_text.py -- 从 SCPT 场景脚本抽取正文/选项（一行＝一次点击）。

SCPT 结构（424/424 文件指令流闭合验证）:
  0x00 'SCPT'
  0x04 u32 0
  0x08 u32 0x20        头长
  0x0C u32 codeSize
  0x10 u32 count
  0x20..0x20+codeSize  指令流：1 字节操作码；0x00/0x01 无操作数，其余带 u32 操作数
  0x20+codeSize..EOF   字符串池：NUL 分隔、每串 4 字节对齐

指令 0x06 = 载入字符串（操作数 = 池内绝对偏移），按代码顺序即上屏顺序。
字符串的用途由紧随其后的调用决定:
  含 0x0A                 -> 正文（一次点击 = 一个框）
  19:12360 (0x3048)       -> 名札（说话人）  → 丢弃
  19:12367/12368/12363/12364/20528/20529 或 04:0 -> 选项
  其余（无 19/04 紧跟）    -> 地点标签 / 资源名  → 丢弃

用法: python scripts/ml2_text.py <dumpdir> <out.txt> [--name 主角名]
"""
import os
import re
import struct
import sys

SCENE = re.compile(r'^E[a-z0-9]\d{3}_\d\d_\d{3}$')   # E0001_00_000 / Ea920_01_000；排除 EV000(调试)
CHOICE_CALLS = {12367, 12368, 12363, 12364, 20528, 20529}
NAME_CALL = 12360


def parse_scpt(b):
    if b[:4] != b'SCPT':
        return
    hs = struct.unpack_from('<I', b, 8)[0]
    cs = struct.unpack_from('<I', b, 12)[0]
    if hs != 0x20 or not (0 < cs < len(b)):
        return
    p, end = 0x20, 0x20 + cs
    while p < end:
        op = b[p]
        if op in (0x00, 0x01):
            yield p, op, None
            p += 1
        else:
            yield p, op, struct.unpack_from('<I', b, p + 1)[0]
            p += 5


def str_at(b, off):
    e = b.find(b'\x00', off)
    if e < 0:
        e = len(b)
    return b[off:e]


def scene_items(b):
    """-> [(kind, bytes)]  kind = 'text' | 'choice'"""
    ins = list(parse_scpt(b))
    out = []
    for i, (p, op, arg) in enumerate(ins):
        if op != 0x06 or arg is None or not (0x20 < arg < len(b)):
            continue
        s = str_at(b, arg)
        if not s:
            continue
        if b'\n' in s:
            out.append(('text', s))
            continue
        for k in (1, 2, 3):
            if i + k >= len(ins):
                break
            o2, a2 = ins[i + k][1], ins[i + k][2]
            if o2 == 0x04:
                out.append(('choice', s))
                break
            if o2 == 0x19:
                if a2 == NAME_CALL:
                    break
                if a2 in CHOICE_CALLS:
                    out.append(('choice', s))
                break
    return out


def clean(s, name):
    t = s.decode('cp932', 'replace')
    t = t.replace('\r', '').rstrip('\n')
    t = t.replace('\n', '')          # 同框换行合并
    t = t.replace('[主人公]', name)
    return t


def extract(dumpdir, name, log=print):
    files = []
    for root, _, fs in os.walk(os.path.join(dumpdir, 'DATA02')):
        if not SCENE.match(os.path.basename(root)):
            continue
        for f in fs:
            if f.lower().endswith('.bin'):
                files.append(os.path.join(root, f))
    files.sort()
    lines = []
    stats = {'files': 0, 'text': 0, 'choice': 0}
    for f in files:
        items = scene_items(open(f, 'rb').read())
        if not items:
            continue
        stats['files'] += 1
        for kind, s in items:
            lines.append(clean(s, name))
            stats[kind] += 1
    out = []
    for l in lines:
        l = l.rstrip()
        if not l:
            continue
        if out and out[-1] == l:      # 连续重复（同串连发）只留一次
            continue
        out.append(l)
    log('files=%d text=%d choice=%d lines=%d' %
        (stats['files'], stats['text'], stats['choice'], len(out)))
    return out


if __name__ == '__main__':
    dump, dst = sys.argv[1], sys.argv[2]
    nm = 'アデライーデ'
    if '--name' in sys.argv:
        nm = sys.argv[sys.argv.index('--name') + 1]
    ls = extract(dump, nm)
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(ls) + '\n')
    print('wrote', dst, len(ls))
