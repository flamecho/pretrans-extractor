#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""うたの☆プリンスさまっ♪ Repeat LOVE（PSV / PCSG00914）全文本提取。

链路（NIS 移植版，自证）：
  pkg2zip -x → psvpfsparser（keystone matched）→ dec/database.dat（NSAC v2）
  NSAC 内 140 条：正文＝memorial_001..112.dat，用語辞典＝common_Story.dat（見出し語 192）
                ＋ DictionaryDataBase.dat（解説 1,099，category 指回見出し語）
  其余（graphics_*.dat / start.dat / sound_*.dat / minigame）经全库 UTF-8 扫描确认无正文。

文本表格式（memorial / MemorialDataBase / DictionaryDataBase 通用）：
  [0x00] u32 n            [0x04] u32 16（表项长）
  [0x08] u32 textOff      [0x0c] u32 32（表头长）
  [0x20] n × 16 B 表项    [textOff] UTF-8 NUL 结尾串
  · 剧情文件表项 = (idx, textRelOff, page, line)；page/line 为派生计数器（每 11 条翻页），无语法义
  · 辞典表项     = (id, category, senseIdx, textRelOff)
  · 空串表项 = 框终止（＝一次点击，清框）；非空表项 = 该框内的一段显示行 ⇒ 直接拼接

主角名占位（CJK 兼容单位符号）：㌫㍊=七海春歌 / ㌫=七海 / ㍊=春歌 / ㌣=春歌
用法: python utapri_rl_extract.py <database.dat> <out.txt>
"""
import os
import re
import struct
import sys

NAME_MAP = [('㌫㍊', '七海春歌'), ('㌫', '七海'), ('㍊', '春歌'), ('㌣', '春歌')]


def nsac_entries(b):
    cnt = struct.unpack_from('<H', b, 6)[0]
    p = 0x26 + cnt * 10
    out = []
    for _ in range(cnt):
        e = b.find(b'\x00', p)
        nm = b[p:e].decode('cp932', 'replace')
        a, o, s = struct.unpack_from('<HII', b, e + 1)
        out.append((nm, o, s))
        p = e + 11
    return out


def str_table(d, i):
    """取第 i 条表项的串（rel offset 相对 textOff）。"""
    to = struct.unpack_from('<I', d, 8)[0]
    rel = struct.unpack_from('<I', d, 32 + i * 16 + 4)[0]
    p = to + rel
    q = d.find(b'\x00', p)
    return d[p:q].decode('utf-8', 'replace')


def named(t):
    for a, b in NAME_MAP:
        t = t.replace(a, b)
    return t


def parse_story(d):
    n = struct.unpack_from('<I', d, 0)[0]
    boxes, cur = [], []
    for i in range(n):
        s = str_table(d, i)
        if s == '':
            if cur:
                boxes.append(named(''.join(cur)))
                cur = []
        else:
            cur.append(s)
    if cur:
        boxes.append(named(''.join(cur)))
    return [b for b in boxes if b.strip(' 　\t')]


def parse_dict(head, expl):
    """解説は**予折行**（1 表項 = 1 显示行，空串 = 段落分隔）⇒ 按見出し語合并成一条。"""
    n = struct.unpack_from('<I', head, 0)[0]
    words = []
    p = 0x2405
    for _ in range(n):
        q = head.find(b'\x00', p)
        words.append(head[p:q].decode('utf-8', 'replace'))
        p = q + 1
        while p < len(head) and head[p] == 0:
            p += 1
    m = struct.unpack_from('<I', expl, 0)[0]
    to = struct.unpack_from('<I', expl, 8)[0]
    buf, order = {}, []
    for i in range(m):
        idx, cat, sub, rel = struct.unpack_from('<4I', expl, 32 + i * 16)
        if not (1 <= cat <= len(words)):
            continue
        q = expl.find(b'\x00', to + rel)
        seg = expl[to + rel:q].decode('utf-8', 'replace').strip(' 　\t')
        if not seg:
            continue
        if cat not in buf:
            buf[cat] = []
            order.append(cat)
        buf[cat].append(seg)
    return ['【%s】%s' % (words[c - 1], ''.join(buf[c])) for c in order]


def main():
    src, dst = sys.argv[1], sys.argv[2]
    b = open(src, 'rb').read()
    ent = {n: b[o:o + s] for n, o, s in nsac_entries(b)}
    # memorial_112 = 楽曲タイトル表（永遠のトライスター／TRUST☆MY DREAM…），非正文
    mem = sorted([n for n in ent if re.match(r'^memorial_\d{3}\.dat$', n)
                  and n != 'memorial_112.dat'])
    print('NSAC 条目 %d；剧情文件 %d' % (len(ent), len(mem)))
    lines = []
    if 'MemorialDataBase.dat' in ent:
        intro = parse_story(ent['MemorialDataBase.dat'])
        lines += intro
        print('  メモリアル導入 %d 框' % len(intro))
    tot = 0
    for nm in mem:
        bx = parse_story(ent[nm])
        tot += len(bx)
        lines += bx
    print('  剧情框 %d（文件 %d）' % (tot, len(mem)))
    dic = []
    if 'common_Story.dat' in ent and 'DictionaryDataBase.dat' in ent:
        dic = parse_dict(ent['common_Story.dat'], ent['DictionaryDataBase.dat'])
    print('  用語辞典 %d 条' % len(dic))
    lines += dic
    txt = '\n'.join(lines) + '\n'
    os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
    open(dst, 'w', encoding='utf-8-sig', newline='\n').write(txt)
    print('-> %s  行数 %d  字 %d' % (dst, len(lines), len(txt)))


if __name__ == '__main__':
    main()
