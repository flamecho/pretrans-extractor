#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""絶対階級学園 ~Eden with roses and phantasm~ (NS) → 提取结果 txt

来源：NSP → Program NCA（titlekey 内容密钥=titlekey）→ RomFS 1/SCRIPT.PAK
记录（L1 自定界）：
  消息 `21 03 | X | Y | Z | n | n×UTF-16LE | 00 00 | mark(u16)`  mark=0x000b(等待点击)/0x0003
  选项 `24 01 | A | B | C | D | E | n | n×UTF-16LE | 00 00`，串内 `$d` 分隔
文本：`` `名前@本文 ``；`$2`=姓(藤枝)/`$3`=名(ネリ)；`$d`=清屏；`$N`/`$n`=排版换行；`$[a$/[b$]`=注音
"""
import struct, re, sys

SRC = '_w_W1_zettaikyuu/out/SCRIPT.PAK'
OUT = '提取结果/[NS-JP]絶対階級学園 ~Eden with roses and phantasm~.txt'
SURNAME, GIVEN = '藤枝', 'ネリ'
LABEL_END = 0x8049          # 0x113a..0x8048 是 843 条「００１…０８４３」标签表
RUBY = re.compile(r'\$\[([^\]$]*)(?:\$/[^\]]*)?\]')


def recs(d):
    out = []
    i, L = 0x10f4, len(d)
    while i < L - 14:
        op = struct.unpack_from('<H', d, i)[0]
        if op == 0x0321:
            X, Y, Z, n = struct.unpack_from('<HHHH', d, i + 2)
            t = i + 10
            if 0 < n < 3000 and t + 2 * n + 6 <= L and d[t + 2 * n:t + 2 * n + 2] == b'\x00\x00' \
                    and d[t + 2 * n + 2:t + 2 * n + 4] in (b'\x0b\x00', b'\x03\x00'):
                try:
                    s = d[t:t + 2 * n].decode('utf-16-le')
                except UnicodeDecodeError:
                    s = None
                if s and all(ord(c) >= 0x20 for c in s):
                    out.append(['m', i, s])
                    i = t + 2 * n + 6
                    continue
        elif op == 0x0124:
            A, B, C, D2, E, n = struct.unpack_from('<HHHHHH', d, i + 2)
            t = i + 14
            # 选项记录指纹：B 恒为 0x177d、E >= 0x4000（实测 77 条全中；其它位置无此组合）
            if B == 0x177d and E >= 0x4000 and 0 < n < 3000 and t + 2 * n + 2 <= L \
                    and d[t + 2 * n:t + 2 * n + 2] == b'\x00\x00':
                try:
                    s = d[t:t + 2 * n].decode('utf-16-le')
                except UnicodeDecodeError:
                    s = None
                if s and all(ord(c) >= 0x20 for c in s):
                    out.append(['c', i, s])
                    i = t + 2 * n + 2
                    continue
        i += 2
    return out


def clean(s):
    if s.startswith('`'):
        j = s.find('@')
        s = s[j + 1:] if 0 < j <= 24 else s[1:]
    elif '@' in s[:24] and not any(c in s[:s.find('@')] for c in '「」『』、。！？…'):
        s = s[s.find('@') + 1:]
    s = RUBY.sub(lambda m: m.group(1), s)
    s = s.replace('$d', '').replace('$N', '').replace('$n', '')
    s = s.replace('$2', SURNAME).replace('$3', GIVEN)
    s = s.replace('$', '').replace('[', '').replace(']', '')
    return s.replace('\u00a0', '\u3000').strip()


def main():
    d = open(SRC, 'rb').read()
    rs = recs(d)
    lines, n_label, n_msg, n_opt = [], 0, 0, 0
    for kind, off, s in rs:
        if kind == 'm':
            if off < LABEL_END and re.fullmatch(r'[０-９]{1,6}', s):
                n_label += 1
                continue
            t = clean(s)
            if t:
                lines.append(t)
                n_msg += 1
        else:
            for part in s.split('$d'):
                t = clean(part)
                if t:
                    lines.append(t)
                    n_opt += 1
    body = '\n'.join(lines) + '\n'
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write(body)
    print('消息 %d / 选项 %d / 标签剔除 %d / 合计行 %d' % (n_msg, n_opt, n_label, len(lines)))
    print('->', OUT)


if __name__ == '__main__':
    main()
