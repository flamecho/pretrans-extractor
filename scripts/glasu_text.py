#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""硝子の森（PS2-JP / D3P SIMPLE2000 Vol.13 / HuneX "ebf" Ver 0.30）文本提取。

链路：ISO9660 → EVENTDAT.BIN（PACK，8 成员）→ 成员内 'LZSS' 块 → ebf 模块

LZSS（与 SLPM_622.34 0x141840 解码器逐指令对照，并与 リプルのたまご 同族 cLz 一致）：
  'LZSS' + u32 blockSize(含 16B 头) + u32 decompSize + u32 0
  flag 字节管 8 个令牌，LSB 优先：bit=1 ⇒ 1 字节字面量
  bit=0 ⇒ [a][b]：窗口基址 = a | ((b & 0xF0) << 4)，长度 = (b & 0xF) + 3
  ★窗口起始位置 0xFEE（不是 0）——上一轮 0 行交付的根因
  解码到 decompSize 或输入耗尽为止

字节码：<op> <argc>（<len> <bytes>）× argc，串长 len 含结尾 NUL
  07 01 <len> <cp932>：显示串（末字节必为 00）
      "\\"   ⇒ 待键换页（点击）        "\\1" ⇒ 清屏换页（选项/换场前）
      结尾 "\\" ⇒ 文本 + 点击          结尾 "@" ⇒ 换页（清屏推进，不等待）
      同一次点击内 1–3 条 07 01 ＝ 同框多行 ⇒ 合并为一行
  18 03 <文本> <标签> <表达式>：选项，一项一条
  09 01 <len> <名>：名札（独立名字窗）⇒ 不取（整行丢弃）
内联控制码 %c84#1 / %c1 / %g-1 / %g-2 剔除。
名字槽：$500/$501 = 名「深鈴」、$502/$503 = 姓「高村」（m0_009 默认值）。
"""
import os
import re
import struct
import sys

NN = 0x1000
WIN_BASE = 0xFEE
NAME_MAP = {'$500': '深鈴', '$501': '深鈴', '$502': '高村', '$503': '高村'}
CTRL = re.compile(r'%[cgw][0-9A-Fa-f#\-]*')
INDENT = '\u3000'


def lzs(src, outsize):
    win = bytearray(NN)
    out = bytearray()
    flags = 0
    i = 0
    dp = WIN_BASE
    n = len(src)
    while i < n and len(out) < outsize:
        flags >>= 1
        if (flags & 0x100) == 0:
            if i >= n:
                break
            flags = src[i] | 0xFF00
            i += 1
        if flags & 1:
            if i >= n:
                break
            c = src[i]
            i += 1
            out.append(c)
            win[dp] = c
            dp = (dp + 1) & (NN - 1)
        else:
            if i + 1 >= n:
                break
            lo = src[i]
            hi = src[i + 1]
            i += 2
            off = lo | ((hi & 0xF0) << 4)
            ln = (hi & 0x0F) + 3
            for t in range(ln):
                if len(out) >= outsize:
                    break
                c = win[(off + t) & (NN - 1)]
                out.append(c)
                win[dp] = c
                dp = (dp + 1) & (NN - 1)
    return bytes(out)


def pack_entries(d):
    n = struct.unpack_from('<I', d, 4)[0]
    out = []
    for i in range(n):
        if 0x18 + i * 8 + 8 > len(d):
            break
        o, s = struct.unpack_from('<II', d, 0x18 + i * 8)
        if o == 0xffffffff:
            break
        out.append((o, s))
    return out


def modules(d):
    for mi, (o, s) in enumerate(pack_entries(d)):
        seg = d[o:o + s]
        p = 0
        bi = 0
        while p + 16 <= len(seg):
            if seg[p:p + 4] != b'LZSS':
                p += 4
                continue
            comp, dec, _u = struct.unpack_from('<III', seg, p + 4)
            if comp < 16 or p + comp > len(seg):
                p += 4
                continue
            yield mi, bi, lzs(seg[p + 16:p + comp], dec)
            p += comp
            bi += 1


def clean(s):
    s = CTRL.sub('', s)
    for k, v in NAME_MAP.items():
        s = s.replace(k, v)
    return s


def scan(b):
    i = 0
    n = len(b)
    while i < n - 1:
        if b[i] == 0x07 and b[i + 1] == 0x01:
            L = b[i + 2]
            if 2 <= L <= 200 and i + 3 + L <= n and b[i + 3 + L - 1] == 0:
                try:
                    t = b[i + 3:i + 3 + L - 1].decode('cp932')
                except UnicodeDecodeError:
                    i += 1
                    continue
                yield ('text', t)
                i += 3 + L
                continue
        elif b[i] == 0x18 and b[i + 1] == 0x03:
            p = i + 2
            args = []
            ok = True
            for _ in range(3):
                if p >= n:
                    ok = False
                    break
                L = b[p]
                if not (2 <= L <= 200) or p + 1 + L > n or b[p + L] != 0:
                    ok = False
                    break
                args.append(b[p + 1:p + L])
                p += 1 + L
            if ok:
                try:
                    t = args[0].decode('cp932')
                except UnicodeDecodeError:
                    ok = False
                if ok:
                    yield ('opt', t)
                    i = p
                    continue
        i += 1


def main():
    src, dst = sys.argv[1], sys.argv[2]
    d = open(src, 'rb').read()

    uniq = []
    seen = set()
    for _mi, _bi, b in modules(d):
        if len(b) > 40 and b[:4] == b'(C) ' and b not in seen:
            seen.add(b)
            uniq.append(b)

    out = []
    stat = dict(box=0, scr=0, click=0, opt=0, merge=0)
    for b in uniq:
        screen = []      # 当前屏的行
        group = []       # 当前点击内的各屏

        def close_screen():
            if not screen:
                return
            pieces = [screen[0]]
            for s in screen[1:]:
                if s.startswith(INDENT):
                    s = s[1:]
                pieces.append(s)
            group.append(''.join(pieces))
            stat['scr'] += 1
            screen.clear()

        def close_group():
            close_screen()
            if not group:
                return
            stat['box'] += 1
            if len(group) > 1:
                stat['merge'] += 1
            out.extend(group)
            group.clear()
            stat['click'] += 1

        for ev in scan(b):
            if ev[0] == 'opt':
                close_group()
                c = clean(ev[1])
                if c.startswith('【') and c.endswith('】'):   # 选项窗的装饰括弧
                    c = c[1:-1]
                if c:
                    out.append(c)
                    stat['opt'] += 1
                continue

            t = ev[1]
            if t in ('\\', '\\1'):
                close_group()
                continue
            if t == '@':
                close_screen()
                continue

            # 前缀：\ / \1 / @ ＝ 先清屏（先断当前屏）
            if t[0] in '\\@':
                close_screen()
                t = t[1:]
                if t[:1] == '1':
                    t = t[1:]
                if t[:1] == '@':
                    close_screen()
                    t = t[1:]
                elif t[:1] == '\\':
                    t = t[1:]

            click = page = False
            if t.endswith('\\1'):
                t = t[:-2]
                click = True
            elif t.endswith('\\'):
                t = t[:-1]
                click = True
            elif t.endswith('@'):
                t = t[:-1]
                page = True

            t = clean(t).strip('@')
            if t and t.strip():
                screen.append(t)
            if click:
                close_group()
            elif page:
                close_screen()

        close_group()

    lines = [l for l in out if l.strip()]
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('模块 %d｜点击 %d｜屏 %d｜多屏点击 %d｜选项 %d｜行 %d'
          % (len(uniq), stat['click'], stat['scr'], stat['merge'],
             stat['opt'], len(lines)))


if __name__ == '__main__':
    main()
