#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""放課後のLove Beat（PS2 / HuneX ADVD, SLPM_655.79）文本提取。

字符串常量格式（实测）：
    [u16 op][u16 n=2+len_dwords][u16 tag][u16 len_dwords][len_dwords*4 字节, NUL 填充]
  tag 0x0103 = 画面文本（台词/选项）    tag 0xcc03 = 路径·名札·系统串·扉文
  op 0x08    = 台词（一框 = 一次点击，框内 0x0A 软换行）
  op 0x00..  = 选项条目（外层 0x64 = 选择肢组，条目 = [u16 pad][u16 n][字符串]）
  op 0x4c    = 名札（独立名字窗）→ 丢弃
  op 0x26    = 扉文/日付カード（上屏特效）→ 收
  op 0x24/25 = メモカ等系统 UI → 丢弃（n≠2+len 的另一套编码）
文本内 \\str1/\\str2 = 主角 姓/名；PUA 0xE0xx = 三点リーダ外字。
"""
import struct, os, sys

SYS = sys.argv[2] if len(sys.argv) > 2 else 'ADVD/SYS'
ORDER = ['ADV_%s.BIN' % c for c in 'ABCDEFGHIJKLMN']
NAME = {'\\str1': '響', '\\str2': 'ルカ'}
PUA = {'\ue000': '…', '\ue008': '…', '\ue07d': '…', '\ue08c': '…', '\ue091': '…'}


def scan(d):
    """按偏移顺序产出 (op, tag, raw_text)。只认 n == 2+len 的自定界字符串记录。"""
    i, n = 0, len(d)
    while True:
        j = d.find(b'\x03', i)
        if j < 0:
            return
        tag = d[j:j + 2]
        if tag in (b'\x03\x01', b'\x03\xcc'):
            wl = struct.unpack_from('<H', d, j + 2)[0]
            cnt = struct.unpack_from('<H', d, j - 2)[0]
            op0 = struct.unpack_from('<H', d, j - 4)[0]
            ok = (cnt == 2 + wl) or (cnt == 0 and op0 in (0x24, 0x25, 0x26))
            if ok and 0 < wl < 800 and j + 4 + wl * 4 <= n:
                raw = d[j + 4:j + 4 + wl * 4].split(b'\x00')[0]
                try:
                    t = raw.decode('cp932')
                except Exception:
                    t = None
                if t is not None:
                    yield op0, tag, t
                i = j + 4 + wl * 4
                continue
        i += 1


def clean(t, escaped_nl=False):
    for ch, rep in PUA.items():
        t = t.replace(ch, rep)
    for k, v in NAME.items():
        t = t.replace(k, v)
    if escaped_nl:
        t = t.replace('\\n', '')
    return t.replace('\n', '').replace('\r', '').strip()


def main(out):
    lines = []
    stat = []
    for fn in ORDER:
        d = open(os.path.join(SYS, fn), 'rb').read()
        nt = no = nc = 0
        for op, tag, t in scan(d):
            if tag == b'\x03\x01' and op == 0x08:
                s = clean(t)
                nt += 1
            elif tag == b'\x03\x01' and op == 0x00:
                s = clean(t)
                no += 1
            elif tag == b'\x03\xcc' and op == 0x26:
                s = clean(t, escaped_nl=True)
                nc += 1
            else:
                continue
            if s:
                lines.append(s)
        stat.append((fn, nt, no, nc))
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    for fn, a, b, c in stat:
        print('%-12s 台词%5d 选项%4d 扉文%4d' % (fn, a, b, c))
    print('total', len(lines))


if len(sys.argv) < 2:
    print('用法: python scripts/lovebeat_extract.py <out.txt> [ADVD/SYS 目录]')
    raise SystemExit(1)
main(sys.argv[1])
