#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""うたの☆プリンスさまっ♪ All Star After Secret (NS/01008030149FE000) 剧本提取。

引擎：Broccoli 自研；脚本 = novel/DATAxx/xx_Story.dat（CRI CPK 内）
  指令流：0xFF <op> <...>；文本记录：
    op 0x0A  头 12B：[2:4] 样式 id(LE)、[4:6]/[6:8] 长度、其后 XOR-SJIS 文本
             样式 0x00CC + 空文本 ⇒ 文本框结束（= 一次点击）
             样式 0x00D5 + 空文本 ⇒ 主角名插入宏
    op 0x00  头 4B，其后文本
    op 0x0E  id 0x0074、头 16B，其后文本 ⇒ 选项行
    0x12–0x24（ruby 记录）头 12B，[8:10]=基底字数(LE)，其后 [基底][全文本]
  文本编码：逐字节 XOR 0xFF（SJIS 全取反）
  控制字：0x876E＝改行(㌻)｜0x32A4/0x32A5/0x32A6＝演出标记(㊤㊥㊦) —— 均剔除
用法: python utapri_extract.py <dir_or_dat> [out.txt] [主角名]
"""
import sys, os, glob

NAME_DEFAULT = '春歌'
DROP = {'\u333b', '\u32a4', '\u32a5', '\u32a6'}  # ㌻ ㊤ ㊥ ㊦
TEXT_IDS = (0x00CC, 0x07DE, 0x00D5)  # op0x0A 承载正文的样式 id


def decode(pay):
    out = []
    i, n = 0, len(pay)
    while i < n:
        b = pay[i] ^ 0xFF
        if (0x81 <= b <= 0x9F) or (0xE0 <= b <= 0xFC):
            if i + 1 < n:
                b2 = pay[i + 1] ^ 0xFF
                try:
                    out.append(bytes([b, b2]).decode('cp932'))
                    i += 2
                    continue
                except UnicodeDecodeError:
                    pass
            out.append('〔%02X〕' % b)
            i += 1
            continue
        if b < 0x20:
            i += 1
            continue
        if 0x20 <= b <= 0x7E:
            out.append(chr(b))
        elif 0xA1 <= b <= 0xDF:
            try:
                out.append(bytes([b]).decode('cp932'))
            except UnicodeDecodeError:
                out.append('〔%02X〕' % b)
        else:
            out.append('〔%02X〕' % b)
        i += 1
    return ''.join(out)


def tokens(d):
    pos = [i for i, b in enumerate(d) if b == 0xFF]
    for k, p in enumerate(pos):
        end = pos[k + 1] if k + 1 < len(pos) else len(d)
        yield d[p:end]


def ruby_text(t):
    """ruby 记录（id 0x07DD）：[基底][00 00 | 改行][基底+正文]，只取上屏全文。"""
    pay = t[12:].rstrip(b'\x00')
    if not pay:
        return ''
    raws = [p for p in pay.split(b'\x00\x00') if p]
    full = decode(raws[-1])
    if len(raws) == 1:
        if '\u333b' in full:
            ps = full.split('\u333b')
            if len(ps) >= 2 and ps[1].startswith(ps[0]):
                full = '\u333b'.join(ps[1:])
        else:
            for L in range(1, len(full) // 2 + 1):
                if full[:L] == full[L:2 * L]:
                    full = full[L:]
                    break
    return full


def is_text(s):
    if not s or '〔' in s:
        return False
    kana = sum(1 for c in s if 0x3040 <= ord(c) <= 0x30FF)
    kanji = sum(1 for c in s if 0x4E00 <= ord(c) <= 0x9FFF)
    return (kana + kanji) >= 2


def parse(d):
    """→ 事件序列 [(kind, text)]，kind: T 文本 / E 框结束 / N 主角名 / O 选项"""
    ev = []
    for t in tokens(d):
        if len(t) < 2:
            continue
        op = t[1]
        if op == 0x0A and len(t) >= 12:
            tid = int.from_bytes(t[2:4], 'little')
            pay = t[12:].rstrip(b'\x00')
            if pay:
                s = decode(pay)
                if tid == 0x00D5 and '〔' not in s:
                    ev.append(('D', s))          # 主角名槽（本框首次出现时插入名字）
                elif tid in TEXT_IDS and '〔' not in s:
                    ev.append(('T', s))
            elif tid == 0x00D5:
                ev.append(('D', ''))
            elif tid == 0x00CC:
                ev.append(('E', ''))
        elif op == 0x00 and len(t) >= 4:
            pay = t[4:].rstrip(b'\x00')
            if pay:
                s = decode(pay)
                if '〔' not in s:
                    ev.append(('T', s))
        elif op == 0x0E and len(t) > 16:
            tid = int.from_bytes(t[2:4], 'little')
            if tid == 0x0074:
                pay = t[16:].rstrip(b'\x00')
                if pay:
                    ev.append(('O', decode(pay)))
        elif op not in (0x0A, 0x00, 0x0E) and len(t) > 13 and \
                int.from_bytes(t[2:4], 'little') == 0x07DD:
            s = ruby_text(t)
            if is_text(s):
                ev.append(('R', s))
    return ev


def build(ev, name):
    out = []
    buf = []
    flagged = [False]     # 本框是否已插入过主角名

    def flush():
        if buf:
            s = ''.join(buf)
            for c in DROP:
                s = s.replace(c, '')
            s = s.strip()
            if s:
                out.append(s)
            buf.clear()
            flagged[0] = False

    for kind, txt in ev:
        if kind == 'T' or kind == 'R':
            buf.append(txt)
        elif kind == 'D':
            if not flagged[0]:
                buf.append(name + txt)
                flagged[0] = True
            else:
                buf.append(txt)
        elif kind == 'O':
            flush()
            s = ''.join(ch for ch in txt if ch not in DROP).strip()
            if s:
                out.append(s)
        elif kind == 'E':
            flush()
    flush()
    return out


def main():
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else None
    name = sys.argv[3] if len(sys.argv) > 3 else NAME_DEFAULT
    if os.path.isdir(src):
        files = sorted(glob.glob(os.path.join(src, 'DATA*', '*Story.dat')))
    else:
        files = [src]
    lines = []
    for f in files:
        bs = build(parse(open(f, 'rb').read()), name)
        lines.extend(bs)
        print('%s: %d 行' % (os.path.basename(f), len(bs)))
    txt = '\n'.join(lines) + '\n'
    if dst:
        os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
        open(dst, 'w', encoding='utf-8-sig', newline='\n').write(txt)
    print('合计 %d 行 / %d 字' % (len(lines), len(txt)))


if __name__ == '__main__':
    main()
