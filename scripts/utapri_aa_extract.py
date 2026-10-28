#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""うたの☆プリンスさまっ♪ Amazing Aria & Sweet Serenade LOVE (NS 0100D4300EBF8000)
剧本提取 —— 本作专用，勿与他作/共用工具混用（参考实现 Debut/All Star，但本作的记录集已逐项自证）。

链路: romfs/sn.bin → 首 4B = 解压尺寸 (6,962,112) → LZSS (环 0x1000 / 起点 0xFEE / 8 token 一 flag)
      平铺 = 80 段 chunk 头表 (16 B/条, 0x0000–0x0500, [u32 off][u32 size][8B 0])，Σsize == 解压尺寸
      chunk 0 数据自 0x500 起；记录流跨 chunk 连续。

记录（L0，本作实测计数见 --stats）:
  开框      : 4F 0D 00 <u16 flag>          flag=1 → 随后有名札
  名札      : 46 0D 00 <cp932> NUL         独立名字窗 ⇒ 丢弃（另有 9F 0D 00 变体 24 条）
  正文      : 45 FF FF <u16 序号> <cp932> NUL                41,008 条，与收框 1:1
  正文(歌)  : 9F FF FF <u16 序号> <cp932> NUL                    99 条，同框成组
  收框      : 4A FF FF 6A FF FF FF FF 49 FF FF FF FF        「一次点击」＝清框
  同框不清框: 48 FF FF                                       9 处（全在 9F 歌场景内）
  扉文/章题 : 2E 55 <u32> 01 <u32> <cp932> NUL 3B <u16> 00 … 89 条（章题 + ルートED + 追加要素题卡）
  选项      : 31 80 80 <u32 n> + n × (01 00 <u16 idx> 00 00 <u32> <text> NUL)
  不收      : 32 80 80 / 01 00 FF FF（场景选择・debug 菜单）、4E 0D 00/4E FF FF（版面指令）、
              2D/2E/36/37/44/51/1A–1F/22/23/25（演出・参数指令）

断行判据: L0 —— 收框 49 FF FF FF FF；同框 48 FF FF 与「4F…49 之间无 49」同为不清框。
输出     : 双版对照（同框先列各段，再列合并行；单段框不重复），%N 为框内换行 ⇒ 删并。
主角名   : 宏 ●●●○○○=七海春歌 / ●●●=七海 / ○○○=春歌 / ◎◎◎=春歌（可改名 ⇒ 必须替换）

用法: python utapri_aa_extract.py <sn.bin> <out.txt> [--stats] [--all]
"""
import os
import re
import struct
import sys

NAME_MAP = [
    ('●●●○○○', '七海春歌'),
    ('●●●', '七海'),
    ('○○○', '春歌'),
    ('◎◎◎', '春歌'),
]

# 区域划分（按扉文偏移；两作合集 ⇒ 分作统计用）
REGIONS = [
    ('共通プロローグ', 0x000500, 0x00CCDC),
    ('AA 音也', 0x00CCDC, 0x0A13AF),
    ('AA 真斗', 0x0A13AF, 0x13B19B),
    ('AA 那月', 0x13B19B, 0x1C9768),
    ('SS トキヤ', 0x1C9768, 0x25E47F),
    ('SS レン', 0x25E47F, 0x2D80EB),
    ('SS 翔', 0x2D80EB, 0x37F20B),
    ('AA セシル', 0x37F20B, 0x40A72B),
    ('SS 林檎', 0x40A72B, 0x49E24B),
    ('SS 龍也', 0x49E24B, 0x52FCD0),
    ('AA 光男', 0x52FCD0, 0x594190),
    ('LOVE 追加', 0x594190, 1 << 32),
]
AA = ('共通プロローグ', 'AA 音也', 'AA 真斗', 'AA 那月', 'AA セシル', 'AA 光男')
SS = ('SS トキヤ', 'SS レン', 'SS 翔', 'SS 林檎', 'SS 龍也')


def lzss(src, size, start=0, wstart=0xFEE):
    out = bytearray()
    win = bytearray(0x1000)
    pos = wstart
    i, n = start, len(src)
    while len(out) < size and i < n:
        flags = src[i] | 0xFF00
        i += 1
        for _ in range(8):
            if len(out) >= size:
                break
            if flags & 1:
                if i >= n:
                    return bytes(out)
                b = src[i]
                i += 1
                out.append(b)
                win[pos] = b
                pos = (pos + 1) & 0xFFF
            else:
                if i + 1 >= n:
                    return bytes(out)
                lo, hi = src[i], src[i + 1]
                i += 2
                idx = lo | ((hi & 0xF0) << 4)
                for _ in range((hi & 0x0F) + 3):
                    b = win[idx & 0xFFF]
                    out.append(b)
                    win[pos] = b
                    pos = (pos + 1) & 0xFFF
                    idx += 1
                    if len(out) >= size:
                        break
            flags >>= 1
    return bytes(out)


STYLE = re.compile(r'%[CZ]\d*')


def clean(t):
    t = STYLE.sub('', t)          # %Z 样式码（行首/行中皆有）、%C999 颜色码
    t = t.replace('%N', '')
    for a, b in NAME_MAP:
        t = t.replace(a, b)
    t = ''.join(c for c in t if ord(c) >= 0x20)
    return t.strip()


def dec(o, i, skip=5):
    e = o.find(b'\x00', i + skip)
    return o[i + skip:e].decode('cp932', 'replace'), e


def parse(o):
    """→ [(offset, kind, text)]；kind: T 正文 / C 收框 / H 扉文 / O 选项"""
    ev = []
    for op in (b'\x45', b'\x9f'):
        pat = op + b'\xff\xff'
        p = 0
        while True:
            i = o.find(pat, p)
            if i < 0:
                break
            t, _ = dec(o, i)
            ev.append((i, 'T', t))
            p = i + 3

    p = 0
    while True:
        i = o.find(b'\x49\xff\xff\xff\xff', p)
        if i < 0:
            break
        ev.append((i, 'C', ''))
        p = i + 5

    # 扉文 / 章题卡：2E 55 <u32> 01 <u32> <cp932> NUL 3B <u16> 00 ...
    p = 0
    cards = 0
    while True:
        i = o.find(b'\x2e\x55', p)
        if i < 0:
            break
        if i + 11 < len(o) and o[i + 6] == 1:
            t, e = dec(o, i, 11)
            if e > i + 11 and o[e + 1] == 0x3B and o[e + 4:e + 6] == b'\x98\x0b':
                ev.append((i, 'H', t))
                cards += 1
            elif e > i + 11 and o[e + 1] == 0x3B and abs(struct.unpack('<h', o[e + 2:e + 4])[0]) < 200:
                # 同一扉文指令的另一种收尾（3B <u16> 00 后直接接别的指令）
                ev.append((i, 'H', t))
                cards += 1
        p = i + 1

    # 选项
    groups = 0
    opts = 0
    p = 0
    while True:
        i = o.find(b'\x31\x80\x80', p)
        if i < 0:
            break
        n = struct.unpack('<I', o[i + 3:i + 7])[0]
        if n <= 32:
            q = i + 7
            ok = True
            local = []
            for _ in range(n):
                if o[q:q + 2] != b'\x01\x00':
                    ok = False
                    break
                t, e = dec(o, q, 10)
                local.append((q, 'O', t))
                q = e + 1
            if ok:
                groups += 1
                opts += len(local)
                ev.extend(local)
        p = i + 3

    ev.sort(key=lambda x: x[0])
    stats = dict(cards=cards, opt_groups=groups, opts=opts)
    return ev, stats


def build(ev):
    """→ (对照版行, 点击版行数, 页版行数, 多段框多出段数, [(行, 区域)])"""
    out = []
    where = []
    buf = []
    buf_off = [0]
    click = 0
    page = 0
    multi = 0
    boxes = 0
    mboxes = 0

    def flush():
        nonlocal click, page, multi, boxes, mboxes
        if not buf:
            return
        segs = [s for s in buf if s]
        buf.clear()
        if not segs:
            return
        rg = region(buf_off[0])
        boxes += 1
        if len(segs) == 1:
            out.append(segs[0])
            where.append(rg)
            click += 1
            page += 1
        else:
            for s in segs:
                out.append(s)
                where.append(rg)
            out.append(''.join(segs))
            where.append(rg)
            click += len(segs)
            page += 1
            multi += len(segs) - 1
            mboxes += 1

    for off, kind, t in ev:
        if kind == 'T':
            s = clean(t)
            if s:
                if not buf:
                    buf_off[0] = off
                buf.append(s)
        elif kind == 'C':
            flush()
        else:
            flush()
            s = clean(t)
            if s:
                out.append(s)
                where.append(region(off))
                click += 1
                page += 1
                boxes += 1
    flush()
    return out, click, page, multi, where, boxes, mboxes


def region(off):
    for name, a, b in REGIONS:
        if a <= off < b:
            return name
    return '?'


def main():
    src, dst = sys.argv[1], sys.argv[2]
    d = open(src, 'rb').read()
    if src.lower().endswith('.dec'):
        o = d
    else:
        o = lzss(d, struct.unpack('<I', d[:4])[0], 4)
    ev, st = parse(o)
    lines, click, page, multi, where, boxes, mboxes = build(ev)

    txt = '\n'.join(lines) + '\n'
    os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
    open(dst, 'w', encoding='utf-8-sig', newline='\n').write(txt)

    print('平铺 %d B | 记录 %d | 扉文 %d | 选项 %d 组/%d 条'
          % (len(o), len(ev), st['cards'], st['opt_groups'], st['opts']))
    print('对照版 %d 行 = 点击版 %d + 多段框 %d 个 | 页版 %d | 框 %d 个（多段 %d 个，多出 %d 段）'
          % (len(lines), click, mboxes, page, boxes, mboxes, multi))
    print('字节 %d' % len(txt.encode('utf-8')))
    if '--stats' in sys.argv:
        from collections import Counter
        c = Counter(where)
        for name, a, b in REGIONS:
            if name in c:
                print('  %-14s %d 行' % (name, c[name]))
        aa = sum(c[n] for n in AA)
        ss = sum(c[n] for n in SS)
        print('  Amazing Aria  %d 行 ｜ Sweet Serenade %d 行 ｜ 追加 %d 行'
              % (aa, ss, c.get('LOVE 追加', 0)))


if __name__ == '__main__':
    main()
