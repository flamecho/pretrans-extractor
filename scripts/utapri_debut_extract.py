#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""うたの☆プリンスさまっ♪ Debut (NS 010088200EFE8000) 剧本提取（本作专用，勿与他作共用）。

链路: romfs/sn.bin → LZSS(0x1000 环 / 0xFEE 起点 / 首 4B=解压尺寸) → 平铺(7,812,096 B)
     平铺 = 75 段 chunk 的 (off,size) 头表（16 B/条，0x4B0 起），记录流跨 chunk 连续

记录（L0，实测本作）:
  开框      : 4F 0D 00 <u16 flag>        flag=1 → 名札；0 → 直接正文
  名札      : 46 0D 00 <cp932> NUL        独立名字窗 ⇒ 丢弃
  正文      : 45 FF FF <u16 序号> <cp932> NUL
              收框固定 = 4A FF FF 6A FF FF FF FF 49 FF FF FF FF（46,761/46,761 全命中）
              同框等待 = 同上但末字节为 48 FF FF（全篇 23 处）⇒ 下一条正文与本条同框，须合并
  歌曲场景  : 9F 0D 00 <名札> NUL / 9F FF FF <u16 序号> <cp932> NUL   （同 4F/45 的变体）
  信件署名  : 95 FF FF <u16 序号> <cp932> NUL                       （第三种文本 op，1 条）
  扉文      : 55 <u32> 01 <u32> <cp932> NUL  后接 3B <u16> 00 98 0B 00 D0 80
  选项      : 31 80 80 <u32 n> 之后 n 条 `01 00 <u16 idx> 00 00 <u32> <cp932> NUL`
  另有 86 01/86 02（歌曲场景的整屏字幕卡：内容与 45/9F 重复）⇒ 不收，
       32 80 80（debug 场景选择表）/ 01 00 FF FF（同表条目）⇒ 系统・调试，不收

成行判据: L0（收框 49 指令；48 表示不清框）。%N = 框内改行（删并），%Z = 行首样式码（剥）。
主角名宏: ●●●○○○ = 七海春歌 / ●●● = 七海 / ○○○ = 春歌（默认名取自 main 内 UTF-8 串 七海/春歌）
用法: python utapri_debut_extract.py <sn.bin|sn.dec> <out.txt>
"""
import os
import struct
import sys


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
                ln = (hi & 0x0F) + 3
                for _ in range(ln):
                    b = win[(idx) & 0xFFF]
                    out.append(b)
                    win[pos] = b
                    pos = (pos + 1) & 0xFFF
                    idx += 1
                    if len(out) >= size:
                        break
            flags >>= 1
    return bytes(out)


NAME_MAP = [
    ('●●●○○○', '七海春歌'),
    ('●●●', '七海'),
    ('○○○', '春歌'),
]


def load(path):
    d = open(path, 'rb').read()
    if path.lower().endswith('.dec'):
        return d
    return lzss(d, struct.unpack('<I', d[:4])[0], 4)


def clean(t):
    while t.startswith('%Z'):
        t = t[2:]
    t = t.replace('%N', '')
    for a, b in NAME_MAP:
        t = t.replace(a, b)
    t = ''.join(c for c in t if ord(c) >= 0x20)
    return t.strip()


def dec(seg):
    try:
        return seg.decode('cp932')
    except Exception:
        return None


def parse(o):
    """返回 [offset, kind, text, 是否承接上一条（同框换行）]。

    同框判据（L0）：本记录 opcode 之前的 16 B 内出现 `48 FF FF`
    —— 该码出现在上一条正文尾部、且全篇仅 23 处，后面紧跟的下一条正文即「同框换行/同框等待」，
    显示上不清框（对照：`49 FF FF FF FF` = 本框结束＝一次点击）。故须与本条合并成一行。
    """
    recs = []

    # ---- 正文 45 / 9F / 95（三种文本 op，均 <op> FF FF <u16 序号> <cp932> NUL）----
    for op in (b'\x45', b'\x9f', b'\x95'):
        pat = op + b'\xff\xff'
        pos = 0
        while True:
            i = o.find(pat, pos)
            if i < 0:
                break
            e = o.find(b'\x00', i + 5)
            t = dec(o[i + 5:e])
            if t:
                cont = b'\x48\xff\xff' in o[max(0, i - 16):i]
                recs.append([i, 'msg', t, cont])
            pos = i + 3

    # ---- 扉文 / 章节卡 55 ----
    pos = 0
    while True:
        k = o.find(b'\x2e\x55', pos)
        if k < 0:
            break
        i = k + 1
        if o[i + 5] == 0x01:
            e = o.find(b'\x00', i + 10)
            t = dec(o[i + 10:e]) if 0 < e - (i + 10) < 40 else None
            tail = o[e + 1:e + 9]
            if t and tail[0] == 0x3b and tail[3:5] == b'\x98\x0b' and tail[6:8] == b'\xd0\x80':
                recs.append([i, 'title', t, False])
        pos = i + 1

    # ---- 选项 ----
    pos = 0
    while True:
        i = o.find(b'\x31\x80\x80', pos)
        if i < 0:
            break
        n = struct.unpack('<I', o[i + 3:i + 7])[0]
        q = i + 7
        for _ in range(n):
            if o[q:q + 2] != b'\x01\x00':
                break
            e = o.find(b'\x00', q + 10)
            t = dec(o[q + 10:e])
            if t:
                recs.append([q, 'opt', t, False])
            q = e + 1
        pos = i + 3

    recs.sort(key=lambda x: x[0])
    return recs


def main():
    src = sys.argv[1]
    dst = sys.argv[2]
    o = load(src)
    recs = parse(o)
    merged = []
    for off, kind, t, cont in recs:
        t = clean(t)                      # 先各自清洗（剥 %Z / %N / 占位符），再合并
        if merged and kind == 'msg' and cont:
            merged[-1][2] += t
        else:
            merged.append([off, kind, t])
    lines = [r[2] for r in merged if r[2]]
    txt = '\n'.join(lines) + '\n'
    os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
    open(dst, 'w', encoding='utf-8-sig', newline='\n').write(txt)
    kinds = {}
    for r in merged:
        k = r[1]
        kinds[k] = kinds.get(k, 0) + 1
    print('平铺 %d B -> %d 行 / %d 字  %s' % (len(o), len(lines), len(txt), kinds))


if __name__ == '__main__':
    main()
