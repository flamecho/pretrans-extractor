#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Starry☆Sky PSV（Summer/Autumn/Winter Stories, PCSG00916/917/918）剧本文本提取。

链路：PSV NoNpDrm pkg → pkg2zip -x → psvpfsparser(keystone matched) → dec/data/sn.bin
      sn.bin = [u32 解压尺寸] + LZSS(环 0x1000／起点 0xFEE／8 token 一 flag)
      平铺 = 717 段 chunk 头表（16B/条：[u32 off][u32 size][8B 0]），chunk 0 数据自 0x2CD0
      剧本流跨 chunk 连续，按文件偏移即阅读顺序（chunk 0 头部为 debug 场景菜单，不收）。

记录（本作实测）：
  开框   4F 0D 00 <u16 flag>                     flag=1 ⇒ 随后有独立名札
  名札   46 0D 00 <cp932> NUL                    独立名字窗 ⇒ 丢弃
  正文   45 FF FF <u16 序号> <cp932> NUL          38,144 条（主）
         45 0A 00 <u16 序号> <cp932> NUL          32 条（旁白／引用变体）
         45 46 00 <cp932> NUL                     18 条（手纸ページ，5 字节内无序号）
         47 46 00 <cp932> NUL                     2 条
  收框   4A FF FF 6A FF FF FF FF                 38,710（每条正文后 1:1）
  点击   49 FF FF FF FF                           清框＝一次点击
  等待   48 46 00（手纸页内不清框）                ⇒ 每页仍各占一次点击
  选项   31 80 80 <u32 n> + n×(01 00 <u16> 00 00 <u32 hash> <cp932> NUL)
  不收   32 80 80（debug 场景选择表：本編スタート／ファイル実行／実験場…）、
         01 00 FF FF（同表条目）、演出/参数指令（0x0F–0x2D/0x34/0x39/0x44/0x59…）

成行：一行 = 一次点击；%N = 框内软换行 ⇒ 删除合并。名札丢弃、不加说话人前缀。
用法：python scripts/ss_psv_extract.py <sn.bin> <out.txt> [--stats]
"""
import os
import re
import struct
import sys

JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
DEBUG_MARK = ('本編スタート', 'ファイル実行', '実験場', '作成中ファイル')


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
                    b = win[idx & 0xFFF]
                    out.append(b)
                    win[pos] = b
                    pos = (pos + 1) & 0xFFF
                    idx += 1
                    if len(out) >= size:
                        break
            flags >>= 1
    return bytes(out)


def load(path):
    d = open(path, 'rb').read()
    if path.lower().endswith('.dec'):
        return d
    size = struct.unpack('<I', d[:4])[0]
    return lzss(d, size, 4)


def dec(b):
    try:
        return b.decode('cp932')
    except Exception:
        return None


def collect_texts(o):
    """返回 [(offset, kind, text)]；kind: msg / opt。"""
    recs = []

    def add(off, s, e, kind='msg'):
        if e <= s or e - s > 400:
            return
        t = dec(o[s:e])
        # 「……」/「！？」这类无假名无汉字的台词也属正文 ⇒ 判据放宽：含 U+3000 以上或省略号/破折号
        if not t or not any(ord(c) >= 0x3000 or c in '…―─‐' for c in t):
            return
        # 注：debug 场景选择表（32 80 80 + 01 00 FF FF 条目）结构不同，本就不入此处，
        #     故不得按「実験場」等关键词过滤正文（Winter 有正文含「実験場」）。
        recs.append((off, kind, t))

    # ---- 正文：45 FF FF / 45 0A 00（+u16 序号）----
    for pat in (b'\x45\xff\xff', b'\x45\x0a\x00'):
        pos = 0
        while True:
            i = o.find(pat, pos)
            if i < 0:
                break
            pos = i + 1
            s = i + 5
            e = o.find(b'\x00', s)
            if e > 0:
                add(i, s, e)

    # ---- 正文：45 46 00 / 47 46 00（手纸，无序号）----
    for pat in (b'\x45\x46\x00', b'\x47\x46\x00'):
        pos = 0
        while True:
            i = o.find(pat, pos)
            if i < 0:
                break
            pos = i + 1
            s = i + 3
            e = o.find(b'\x00', s)
            if e > 0:
                add(i, s, e)

    # ---- 选项 ----
    # 31 80 80 <u32 n> + n×(<u16 op><u16 idx><u16 0><u32 hash><cp932> NUL)
    #   op = 01 00 普通项／00 80–05 80 人物选择项／5E 80 锁定项（实测三种，均须收）
    pos = 0
    while True:
        i = o.find(b'\x31\x80\x80', pos)
        if i < 0:
            break
        pos = i + 3
        n = struct.unpack('<I', o[i + 3:i + 7])[0]
        if not 0 < n <= 8:
            continue
        q = i + 7
        for _ in range(n):
            if o[q + 4:q + 6] != b'\x00\x00':
                break
            s = q + 10
            e = o.find(b'\x00', s)
            if e < 0:
                break
            add(q, s, e, 'opt')
            q = e + 1
    return recs


def clean(t):
    t = t.replace('%N', '')
    t = ''.join(c for c in t if ord(c) >= 0x20)
    return t.strip()


def build_dual(o, out):
    """双版对照：仅把「同一框内多段（无 49 清框，48 框内等待/换页）」的框展开为 A/B/C + 合并行；
    单段框只出现一次（不重复）。"""
    rows = []
    cur = []
    for off, kind, t in out:
        if kind != 'msg':
            if cur:
                rows.append(cur)
                cur = []
            rows.append([(off, kind, t)])
            continue
        if cur and b'\x49\xff\xff\xff\xff' not in o[cur[-1][0]:off]:
            cur.append((off, kind, t))
        else:
            if cur:
                rows.append(cur)
            cur = [(off, kind, t)]
    if cur:
        rows.append(cur)
    lines = ['# 双版对照（仅多段框展开；A/B/C…= 逐段，ABC…= 合并）']
    n_multi = 0
    for r in rows:
        if len(r) == 1:
            lines.append(r[0][2])
        else:
            n_multi += 1
            for i, (_, _, t) in enumerate(r):
                lines.append('%s: %s' % (chr(65 + i), t))
            lines.append('%s: %s' % (''.join(chr(65 + i) for i in range(len(r))),
                                     ''.join(t for _, _, t in r)))
    return '\n'.join(lines) + '\n', n_multi


def main():
    src, dst = sys.argv[1], sys.argv[2]
    stats = '--stats' in sys.argv
    dual = '--dual' in sys.argv
    o = load(src)
    recs = collect_texts(o)
    recs.sort(key=lambda r: r[0])
    seen = set()
    out = []
    for off, kind, t in recs:
        c = clean(t)
        if not c:
            continue
        key = (off, c)
        if key in seen:
            continue
        seen.add(key)
        out.append((off, kind, c))
    txt = '\n'.join(r[2] for r in out) + '\n'
    os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
    open(dst, 'w', encoding='utf-8-sig', newline='\n').write(txt)
    print('平铺 %d B → %d 行 / %d 字' % (len(o), len(out), len(txt)))
    if dual:
        dtxt, nm = build_dual(o, out)
        dpath = dst[:-4] + '_双版.txt' if dst.lower().endswith('.txt') else dst + '_双版.txt'
        open(dpath, 'w', encoding='utf-8-sig', newline='\n').write(dtxt)
        print('双版对照：%d 个多段框 → %s' % (nm, dpath))
    if stats:
        import collections
        print(collections.Counter(r[1] for r in out))
        print('前 5 行:', [r[2][:30] for r in out[:5]])


if __name__ == '__main__':
    main()
