#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""闇色の魔珠 (Daisy2 / PROTOTYPE NS) SCRIPT.PAK → 全文本（双版对照）

引擎：B-cluster 自研 PAK 脚本流（同 Re;quartz零度）
记录形状（L1 自定界：u16 长度前缀 ＋ 00 00 终止）：
  消息  `24 03 | X(u16) | Y(u16) | Z(u16) | n(u16) | n×UTF-16LE | 00 00 | TT 00 | F(u16)`
        TT = 0x0b 打印后等待（一屏的最后一行）／0x03 打印后继续（同屏追加，不等待）
  选项  `00 40 | n(u16) | n×UTF-16LE | 00 00`，串内 `$d` 分隔各选项，`[(#flag>=n),]` 为解锁条件

成页：一屏 = `0x0b` 收尾；页内 = 其后（或段首）的 `0x03` 串 ＋ 收尾的 `0x0b`
     ⇒ 翻译侧的「段行（每条记录）」＋「合并行（整屏）」
"""
import struct
import re
import os

SRC = '_w_W3_yamiiro/romfs/SCRIPT.PAK'
OUT = '提取结果/[NS-JP]闇色の魔珠.txt'

HEROINE = 'リカ'          # $(3) = 主角名宏（ガリカ・ローサ・スターニス 的通称）
RUBY = re.compile(r'\$\[([^\]$]*)\$/[^\]]*\]|\$\[([^\]]*)\]')
COND = re.compile(r'^\(?\[#[^\]]*\]|^\[\(#[^\]]*\)?,?\]|^\[[^\]]*\]')


def read_str(d, ts, n, N):
    if ts + 2 * n + 2 > N:
        return None
    if d[ts + 2 * n:ts + 2 * n + 2] != b'\x00\x00':
        return None
    try:
        s = d[ts:ts + 2 * n].decode('utf-16le')
    except Exception:
        return None
    if '\x00' in s or '\ufffd' in s:
        return None
    if any(ord(c) < 0x20 and c != '\n' for c in s):
        return None
    return s


def clean(s):
    s = RUBY.sub(lambda m: m.group(1) or m.group(2), s)
    s = re.sub(r'\$K\([^)]*\)', '', s)          # 用語辞書リンク（本体は括弧の外）
    s = s.replace('$(3)', HEROINE)
    s = s.replace('$b', '')
    s = s.replace('$N', '').replace('$n', '')   # 排版换行
    s = s.replace('$', '')                      # 残余单独 `$`＝可选换行点
    s = s.replace('\n', '').replace('\r', '')
    s = s.replace('\u00a0', '\u3000')
    return s.strip()


def strip_name(s):
    """`@名前@本文` → 本文（游戏用独立名字窗，不保留前缀）"""
    if s.startswith('@'):
        e = s.find('@', 1)
        if 0 < e <= 13:
            return s[e + 1:]
    e = s.find('@')
    if 0 < e <= 13 and not any(c in s[:e] for c in '「」『』、。！？…'):
        return s[e + 1:]
    return s


def main():
    d = open(SRC, 'rb').read()
    N = len(d)

    msgs = []
    i = 0
    while True:
        i = d.find(b'\x24\x03', i)
        if i < 0:
            break
        q = i + 8
        if q + 2 <= N:
            n = struct.unpack_from('<H', d, q)[0]
            if 1 <= n <= 900:
                s = read_str(d, q + 2, n, N)
                if s is not None:
                    e = q + 2 + 2 * n + 2
                    msgs.append([i, e + 4, d[e], s])
        i += 2

    opts = []
    i = 0
    while True:
        i = d.find(b'\x00\x40', i)
        if i < 0:
            break
        n = struct.unpack_from('<H', d, i + 2)[0] if i + 4 <= N else 0
        if 2 <= n <= 900:
            s = read_str(d, i + 4, n, N)
            if s is not None and '$d' in s and any('\u3040' <= c <= '\u30ff' for c in s):
                opts.append([i, i + 4 + 2 * n + 2, s])
        i += 2

    # 选项与正文不重叠；标题画面的章选菜单（UI）剔除
    spans = [(m[0], m[1]) for m in msgs]
    opts = [o for o in opts
            if not o[2].startswith('プロローグから始める')
            and not any(a <= o[0] < b for a, b in spans)]

    events = [(m[0], 0, m) for m in msgs] + [(o[0], 1, o) for o in opts]
    events.sort(key=lambda x: x[0])

    pages = []          # [[(off, text, mark), ...], ...]
    cur = []
    prev03 = False
    n_opt = 0
    for off, kind, rec in events:
        if kind == 1:
            # 选项：独占一屏，逐条拆出
            txt = rec[2]
            for part in txt.split('$d'):
                part = COND.sub('', part).strip()
                part = clean(part)
                if part:
                    pages.append([(off, part, -1)])
                    n_opt += 1
            continue
        mark, txt = rec[2], clean(strip_name(rec[3]))
        if mark == 0x03:
            if not prev03 and cur:
                pages.append(cur)
                cur = []
            if txt:
                cur.append((off, txt, mark))
            prev03 = True
        else:
            if prev03 and cur:
                if txt:
                    cur.append((off, txt, mark))
            else:
                if cur:
                    pages.append(cur)
                    cur = []
                if txt:
                    cur = [(off, txt, mark)]
            prev03 = False
    if cur:
        pages.append(cur)

    lines = []
    nseg = nmerged = 0
    for pg in pages:
        if len(pg) == 1 and pg[0][2] == -1:
            lines.append(pg[0][1])
            continue
        segs = [t for _, t, _ in pg]
        lines.extend(segs)
        nseg += len(segs)
        if len(segs) >= 2:
            lines.append(''.join(segs))
            nmerged += 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(lines) + '\n')

    multi = sum(1 for pg in pages if len(pg) >= 2 and pg[0][2] != -1)
    print('消息 %d  选项记录 %d → %d 行  屏 %d（多段屏 %d）'
          % (len(msgs), len(opts), n_opt, len(pages), multi))
    print('段行 %d  合并行 %d  总行 %d  闭合 %d'
          % (nseg, nmerged, len(lines), nseg + nmerged + n_opt))


if __name__ == '__main__':
    main()
