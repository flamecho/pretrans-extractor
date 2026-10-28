#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VitaminX Destination (PSV-JP, PCSG01115) —— HuneX 'HESL / HESE' 剧本文本提取器
详见 提取结果/解析报告/[PSV-JP]VitaminX Destination_解析报告.md

容器
  script.heslnk  HESL：头 0x30（'HESL',ver,count,unk1,unk2,nameOff,dataOff）
                 条目 @0x30，每项 0x10B（checksum, item_offset, item_size）
                 名称 @nameOff（NUL 分隔）
                 item[0] = 'charset'（CSB\\0）

  CSB   'CSB\\0' + ver + count；字符表 @0x44，每项 **6 字节**（UTF-8 1〜3B + 零填充）
        index → 字符

  HESE  头：magic, ver, code_offset, string_count(=0), text_op_count
        文本指令（4 字节 op + 4 字节 0 + 4 字节 index，随后内联 u16 串）：
            1b 00 00 80 | 00 00 00 00 | <u32 index> | 串
        选项指令（8 字节 + 内联串，param = 跳转目标）：
            19 00 00 80 | <u32 target> | 串
        名札指令（8 字节 + 内联串，param = 名札 id）：
            1a 00 00 80 | <u32 id> | 串        ← 全角拉丁角色 id（'ＧｏｒｏＦｕｍｏｎｊｉ'），按规范丢弃

  串 = u16 码流
        0x0000 / <0x20 / 0x0023 → 串结束
        0x002C / 0x8000        → 框内换行 → 合并
        0xFFFC / 0xFFFF        → 丢弃
        <0x80                  → ASCII
        >=0x8000               → charset[code - 0x8000 - 6]

  ★ 一次 TEXT 指令 = 一个文本框 = 一次点击（hoc = 每条脚本的 text_op_count，逐脚本校验一致）
  ★ 框内无「清框/不清框」第二形态：0x8000 只是显式换行，故不做双版本
"""
import os
import struct
import sys

PH = '〔未解析〕'
TEXT_SIG = b'\x1b\x00\x00\x80\x00\x00\x00\x00'
CHOICE_SIG = b'\x19\x00\x00\x80'
NAME_SIG = b'\x1a\x00\x00\x80'


def load_hesl(path):
    buf = open(path, 'rb').read()
    magic, ver, count, u1, u2, nameoff, dataoff = struct.unpack_from('<5I12x2I8x', buf, 0)
    assert magic == int.from_bytes(b'HESL', 'little'), buf[:4]
    names, o = [], nameoff
    for _ in range(count):
        e = buf.find(b'\0', o)
        names.append(buf[o:e].decode('latin1'))
        o = e + 1
    ents = []
    for k in range(count):
        chk, off, sz = struct.unpack_from('<3I4x', buf, 0x30 + k * 0x10)
        ents.append([names[k], off, sz])
    alloff = sorted(e[1] for e in ents)
    for e in ents:
        if e[2]:
            e.append(e[1] + e[2])
        else:
            nxt = [x for x in alloff if x > e[1]]
            e.append(nxt[0] if nxt else len(buf))
    return buf, ents


def load_charset(buf, ents):
    e = [x for x in ents if x[0] == 'charset'][0]
    csb = buf[e[1]:e[3]]
    assert csb[:4] == b'CSB\0', csb[:8]
    cnt = struct.unpack_from('<I', csb, 8)[0]
    reg = csb[0x44:]
    chars = []
    for i in range(0, cnt * 6, 6):
        cell = reg[i:i + 6].rstrip(b'\x00')
        chars.append(cell.decode('utf-8') if cell else '')
    return chars


def read_codes(sub, st):
    """-> (codes, end_pos)  串在控制码 / 0x0000 处终止"""
    codes, e, n = [], st, len(sub)
    while e + 1 < n:
        c = sub[e] | (sub[e + 1] << 8)
        if c == 0 or c < 0x20 or c == 0x23:
            break
        codes.append(c)
        e += 2
    return codes, e


def make_decoder(chars):
    n = len(chars)

    def dec(codes):
        out = []
        for c in codes:
            if c in (0x2C, 0x8000):          # 框内换行 → 合并
                continue
            if c in (0xFFFC, 0xFFFF):
                continue
            if c < 0x20 or c == 0x23:
                break
            if 0x21 <= c <= 0x24:
                continue
            if c < 0x80:
                out.append(chr(c))
                continue
            idx = c - 0x8000 - 6
            out.append(chars[idx] if 0 <= idx < n and chars[idx] else PH)
        return ''.join(out).strip()
    return dec


SEG_SUR = b'\x1b\x00\x00\x80\x0b\x00\x00\x00'   # 主角「姓」插入（南）
SEG_GIV = b'\x1b\x00\x00\x80\x0a\x00\x00\x00'   # 主角「名」插入（悠里）
SURNAME, GIVEN = '南', '悠里'


def extract_script(sub, dec):
    """按文件顺序返回事件 [(pos, kind, text)]；kind: T=正文 / C=选项 / H=章題（扉文）

    文本框可能由「正文段 + 姓段(0x0b) + 名段(0x0a)」拼成（主角名宏）：
        TEXT '何が『' + 0x0b '先生……』…  →  何が『南先生……』…
    这类分段版与「字面版」（直接写成 南先生）是同一个框的两种写法；
    字面版存在时只留字面版，缺字面版时用分段版拼回（名字 inline）。
    """
    ev, q, n = [], 0, len(sub)
    texts = []          # (pos, plain, composed)
    while True:
        a = sub.find(TEXT_SIG, q)
        b = sub.find(CHOICE_SIG, q)
        cand = [x for x in (a, b) if x >= 0]
        if not cand:
            break
        p = min(cand)
        if p == b and p != a:
            st = p + 8
            v = sub[st] | (sub[st + 1] << 8) if st + 1 < n else 0
            if v >= 0x8000:
                codes, e = read_codes(sub, st)
                t = dec(codes)
                if t:
                    ev.append((p, 'C', t))
                q = e + 2
            else:
                q = p + 4
            continue
        codes, e = read_codes(sub, p + 12)
        t = dec(codes)
        # 紧随其后的姓/名段（0x0000 终止符要先跳过）
        segs, r = [], (e + 2 if sub[e:e + 2] == b'\x00\x00' else e)
        while sub[r:r + 8] in (SEG_SUR, SEG_GIV):
            kind = 'S' if sub[r:r + 8] == SEG_SUR else 'G'
            c2, e2 = read_codes(sub, r + 8)
            segs.append((kind, dec(c2)))
            r = e2
        if segs and t:
            comp = t + ''.join((SURNAME if k == 'S' else GIVEN) + s for k, s in segs)
            texts.append((p, t, comp))
        else:
            if t:
                texts.append((p, t, None))
        q = e + 2
    plain = [x[1] for x in texts if x[2] is None]
    for pos, t, comp in texts:
        if comp is None:
            ev.append((pos, 'T', t))
        elif not any(pt.startswith(t) and len(pt) > len(t) for pt in plain):
            ev.append((pos, 'T', comp))
    # 章題：1b <param=0x26> + 内联串（扉文）
    p = 0
    while True:
        p = sub.find(b'\x1b\x00\x00\x80\x26\x00\x00\x00', p)
        if p < 0:
            break
        codes, e = read_codes(sub, p + 8)
        t = dec(codes)
        if t:
            ev.append((p, 'H', t))
        p = e + 2
    ev.sort(key=lambda x: x[0])
    return ev


def main():
    src = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else None
    buf, ents = load_hesl(src)
    chars = load_charset(buf, ents)
    dec = make_decoder(chars)
    scripts = [e for e in ents if e[0] != 'charset' and not e[0].startswith('test_script')]
    rows, stats, empty = [], [], 0
    for e in scripts:
        sub = buf[e[1]:e[3]]
        hoc = struct.unpack_from('<I', sub, 16)[0]
        ev = extract_script(sub, dec)
        nt = sum(1 for x in ev if x[1] == 'T')
        nt_all = sub.count(TEXT_SIG)
        nc = sum(1 for x in ev if x[1] == 'C')
        nh = sum(1 for x in ev if x[1] == 'H')
        stats.append((e[0], hoc, nt, nc, nh, nt_all))
        for x in ev:
            rows.append((e[0], x[1], x[2]))
    body = sum(s[2] for s in stats)
    ch = sum(s[3] for s in stats)
    hd = sum(s[4] for s in stats)
    print(f'scripts {len(scripts)}  body {body}  choices {ch}  headings {hd}  total {len(rows)}')
    tot_hoc = sum(s[1] for s in stats)
    tot_sig = sum(s[5] for s in stats)
    print(f'text_op_count total {tot_hoc}  TEXT 签名数 {tot_sig}  (空文本 {tot_sig - body})')
    bad = [s for s in stats if s[1] != s[5]]
    if bad:
        print('  ! text_op_count mismatch:', bad)
    if out_path:
        with open(out_path, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write('\n'.join(t for _, _, t in rows) + '\n')
        print('wrote', out_path, len(rows), 'lines')


if __name__ == '__main__':
    main()
