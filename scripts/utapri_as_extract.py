#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""うたの☆プリンスさまっ♪ All Star (NS 0100B3E0149FC000) 剧本提取。

链路: romfs/sn.bin → LZSS(0x1000 环 / 0xFEE 起点 / 首 4B=解压尺寸) → 平铺 → 本脚本

记录（L0，实测）:
  正文: 4F 0D 00 <flag u16>
        flag=1 → 46 0D 00 <名札> NUL      （名札，丢弃）
        其后 → … FF FF <u16> <正文> NUL 4A FF FF 6A FF FF FF FF 49 …  ← 收框＝一次点击
  选项: 01 00 <idx u16> 00 00 <u32> <文本> NUL
  章题: 4F 03 00 00 <文本> NUL          （扉文，收）
  场景选择表: 01 00 FF FF 00 00 <u32> <文本> NUL  （菜单 UI，不收）
  宏: %N = 框内改行（剔除）｜●●●○○○ / ●●● = 主角名占位
用法: python utapri_as_extract.py <sn.bin> <out.txt> [主角名]
"""
import os
import sys

NAME_DEFAULT = '春歌'
FILLERS = ('●●●○○○', '●●●○○', '●●●○', '●●●', '○○○')


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
                for k in range(ln):
                    b = win[(idx + k) & 0xFFF]
                    out.append(b)
                    win[pos] = b
                    pos = (pos + 1) & 0xFFF
                    if len(out) >= size:
                        break
            flags >>= 1
    return bytes(out)


def load(path):
    d = open(path, 'rb').read()
    if path.lower().endswith('.dec'):
        return d
    return lzss(d, int.from_bytes(d[:4], 'little', signed=True), 4)


def dec(seg):
    try:
        return seg.decode('cp932')
    except Exception:
        return None


PUNCT = set('「」『』（）…‥！？。、ー・～―─!?.,')


def is_text(t):
    if any(0x3040 <= ord(c) <= 0x30FF or 0x4E00 <= ord(c) <= 0x9FFF for c in t):
        return True
    return bool(t) and all(c in PUNCT for c in t)


def clean(t, name):
    t = t.replace('%N', '')
    while t.startswith('%Z') or t.startswith('%YE'):
        t = t[3:]
    for f in FILLERS:
        t = t.replace(f, name)
    t = ''.join(c for c in t if ord(c) >= 0x20)
    return t.strip()


def parse(o, name):
    lines = []       # (offset, text)
    names = []

    # ---- 正文 / 名札 / 扉文 ----
    pos = 0
    while True:
        p = o.find(b'\x4f\x0d\x00', pos)
        if p < 0:
            break
        flag = int.from_bytes(o[p + 3:p + 5], 'little')
        q = p + 5
        if flag == 1:
            if o[q:q + 3] != b'\x46\x0d\x00':
                pos = p + 3
                continue
            e = o.find(b'\x00', q + 3)
            if e < 0:
                break
            nm = dec(o[q + 3:e])
            if nm:
                names.append(nm)
            q = e + 1
        k = o.find(b'\xff\xff', q, q + 32)
        if k < 0:
            pos = p + 3
            continue
        t0 = k + 4
        e2 = o.find(b'\x00', t0)
        if e2 < 0:
            break
        t = dec(o[t0:e2])
        term = o[e2 + 1:e2 + 5]
        if t and term[1:3] == b'\xff\xff' and term[0] in (0x4A, 0x9F) and is_text(t):
            lines.append((t0, t))
        pos = e2 + 1

    # ---- 扉文 4F 03 00 00 ----
    pos = 0
    while True:
        p = o.find(b'\x4f\x03\x00\x00', pos)
        if p < 0:
            break
        t0 = p + 4
        e2 = o.find(b'\x00', t0)
        if e2 < 0:
            break
        t = dec(o[t0:e2])
        if t and is_text(t):
            lines.append((t0, t))
        pos = e2 + 1

    # ---- 选项 ----
    i, n = 0, len(o)
    while i < n:
        j = o.find(b'\x00', i)
        if j < 0:
            break
        seg = o[i:j]
        if 2 <= len(seg) <= 200 and o[max(0, i - 10):i - 8] == b'\x01\x00':
            idx = int.from_bytes(o[max(0, i - 8):i - 6], 'little')
            ptr = int.from_bytes(o[max(0, i - 6):i - 2], 'little')
            if idx < 0x20 and ptr < len(o) and o[i - 2:i] == b'\x00\x00':
                t = dec(seg)
                if t and is_text(t):
                    lines.append((i, t))
        i = j + 1

    lines.sort(key=lambda x: x[0])
    out = []
    for _, t in lines:
        c = clean(t, name)
        if len(c) > 1:
            out.append(c)
    return out, names


def main():
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else None
    name = sys.argv[3] if len(sys.argv) > 3 else NAME_DEFAULT
    o = load(src)
    lines, names = parse(o, name)
    txt = '\n'.join(lines) + '\n'
    if dst:
        os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
        open(dst, 'w', encoding='utf-8-sig', newline='\n').write(txt)
    print('平铺 %d B -> %d 行 / %d 字 / 名札 %d 种' % (len(o), len(lines), len(txt), len(set(names))))
    print('名札:', '、'.join(sorted(set(names))[:20]))


if __name__ == '__main__':
    main()
