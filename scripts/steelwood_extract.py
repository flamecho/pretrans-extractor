#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Steel Wood (原宿探偵学園 スチールウッド) DATA/BIN/M*.DAT 剧本提取。

结构（M01 实证）：
  [0x00] u32 data_start=0x10
  [u32 h1][u32 h2][u32 h3]  三块尾偏移，块 = [0x10,h1) [h1,h2) [h2,h3)
  第三块 = 字节码 + 文本池（0x07 记录流）

记录（字节码内联，L0）：
  05 | 03 00 00 00 | <u16 msgid> | 07 | [1C <name> 11 [1E <6B voice>]] <text> 00
文本编码：
  0x28-0x7A 单字节平假名（cp932 低位 = b+0x77）
  0x81-0x9F / 0xE0-0xEF cp932 双字节（汉字・全角记号）
  0xA1-0xDF 半角片假名（交付前 NFKC 升全角）
  0x11 框内软换行（合并）
  0x12 0x10 框内换页（＝一次点击边界，L0）

选项（块3 内联，12 字节／条，按显示顺序）：
  09 15 <u32 文本指针> 13 10 <u32 optid>
  文本指针基数 = 块3 起点 h2；optid 从 50 起递增，回 50 或码位不连续 = 新的一组菜单。
"""
import struct, sys, os, glob, unicodedata

KANA_LO, KANA_HI = 0x28, 0x7A
MC_GIVEN = '亜希'          # 主角 堀北亜希（ELF 名表锚定），01 39 宏 = 名
PAGE = b'\x12\x10'
LINE = 0x11


def dec_text(seg):
    """返回 (行列表, 是否含未知字节)"""
    out = []
    lines = ['']
    i = 0
    n = len(seg)
    unknown = False
    while i < n:
        c = seg[i]
        if c == LINE:
            i += 1                      # 软换行 -> 合并
            continue
        if seg[i:i + 2] == PAGE:
            lines.append('')            # 换页 -> 新行（L0；引擎每页重印「，续页那份由上段去重）
            i += 2
            continue
        if c == 0x01:                   # 行内宏 01 39 = 主角名（可改名）
            if i + 1 < n and seg[i + 1] == 0x39:
                lines[-1] += MC_GIVEN
            i += 2
            continue
        if c == 0x09:                   # 控制 09 30 xx
            i += 3
            continue
        if c in (0x12, 0x13, 0x16):     # 双字节控制
            i += 2
            continue
        if c == 0x1C:                   # 行内名札（换页后重设说话人）-> 丢弃
            k = seg.find(b'\x11', i + 1)
            if k < 0:
                unknown = True
                i += 1
                continue
            i = k + 1
            if i < n and seg[i] == 0x1E:
                i += 7
            continue
        if KANA_LO <= c <= KANA_HI:
            lines[-1] += bytes([0x82, c + 0x77]).decode('cp932', 'replace')
            i += 1
            continue
        if 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xEF:
            if i + 1 < n:
                ch = seg[i:i + 2].decode('cp932', 'replace')
                lines[-1] += ch
                i += 2
                continue
            unknown = True
            i += 1
            continue
        if 0xA1 <= c <= 0xDF:
            lines[-1] += bytes([c]).decode('cp932', 'replace')
            i += 1
            continue
        unknown = True
        i += 1
    return lines, unknown


def nfkc_kana(s):
    out = []
    for ch in s:
        if 0xFF61 <= ord(ch) <= 0xFF9F:
            out.append(unicodedata.normalize('NFKC', ch))
        else:
            out.append(ch)
    return ''.join(out)


def records(b, lo, hi):
    """产出 (msgid, name_or_None, [lines], unk, 记录尾偏移)，按字节码顺序（＝显示顺序）"""
    i = lo
    while True:
        j = b.find(b'\x07', i, hi)
        if j < 0:
            break
        if b[j - 6:j - 2] != b'\x03\x00\x00\x00':
            i = j + 1
            continue
        mid = struct.unpack_from('<H', b, j - 2)[0]
        p = j + 1
        name = None
        if p < hi and b[p] == 0x1C:
            k = b.find(b'\x11', p + 1, hi)
            if k < 0:
                i = j + 1
                continue
            name = b[p + 1:k]
            p = k + 1
            if p < hi and b[p] == 0x1E:
                p += 7
        e = b.find(b'\x00', p, hi)
        if e < 0:
            break
        lines, unk = dec_text(b[p:e])
        yield mid, name, lines, unk, e
        i = e + 1


def options(b, lo, hi):
    """返回 [[(显示点偏移, 选项文本)]...]，每组菜单一项，按码流顺序。

    校验：`09 15` 后必须紧跟 `13 10`，且 u32(块内相对) 指向能解码的文本；
    文本解不出／为空（图片式无字选项）→ 跳过该条。
    """
    ents = []
    i = lo
    while True:
        i = b.find(b'\x09\x15', i, hi)
        if i < 0:
            break
        if i + 12 <= hi and b[i + 6:i + 8] == b'\x13\x10':
            v = struct.unpack_from('<I', b, i + 2)[0]
            t = lo + v
            if lo <= t < hi:
                e = b.find(b'\x00', t, hi)
                if e > t:
                    ls, unk = dec_text(b[t:e])
                    s = nfkc_kana(''.join(ls)).strip()
                    if s and not unk:
                        ents.append((i, s, struct.unpack_from('<I', b, i + 8)[0]))
        i += 1
    gs, cur = [], []
    for o in ents:
        if cur and not (o[2] == cur[-1][2] + 1 and o[0] == cur[-1][0] + 12):
            gs.append(cur)
            cur = []
        cur.append(o)
    if cur:
        gs.append(cur)
    return [[(o[0], o[1]) for o in g] for g in gs]



def main():
    src = sys.argv[1] if len(sys.argv) > 1 else r'_work_steel/PSP_GAME/USRDIR/DATA/BIN'
    dst = sys.argv[2] if len(sys.argv) > 2 else r'_work_steel/out'
    os.makedirs(dst, exist_ok=True)
    files = sorted(glob.glob(os.path.join(src, 'M*.DAT')))
    allout = []
    stat = []
    for f in files:
        b = open(f, 'rb').read()
        h = struct.unpack_from('<4I', b, 0)
        if h[3] != len(b):
            h = h + (len(b),)
        lo, hi = h[2], min(h[3], len(b))
        base = os.path.basename(f)[:-4]
        lines = []
        nrec = 0
        nunk = 0
        nopt = 0
        recs = list(records(b, lo, hi))
        # 选项菜单 -> 锚定到「显示点之前最近一条记录」= 问句那一框的尾部
        buckets = {}
        ri = 0
        for g in options(b, lo, hi):
            off = g[0][0]
            while ri < len(recs) and recs[ri][4] <= off:
                ri += 1
            buckets.setdefault(ri - 1, []).append(g)
        for g in buckets.pop(-1, []):
            for _, s in g:
                lines.append(s)
                nopt += 1
        for idx, (mid, name, ls, unk, end) in enumerate(recs):
            nrec += 1
            if unk:
                nunk += 1
            depth = 0
            for s in ls:
                s = nfkc_kana(s).strip()
                if not s:
                    continue
                # 换页续页重复开引号（引擎每页重印「）-> 结构去重
                if depth > 0 and s.startswith('\u300c'):
                    s = s[1:]
                depth += s.count('\u300c') - s.count('\u300d')
                if s:
                    lines.append(s)
            for g in buckets.get(idx, []):
                for _, s in g:
                    lines.append(s)
                    nopt += 1
        for g in buckets.get(len(recs), []):
            for _, s in g:
                lines.append(s)
                nopt += 1
        stat.append((base, nrec, nunk, nopt, len(lines), sum(len(x) for x in lines)))
        with open(os.path.join(dst, base + '.txt'), 'w', encoding='utf-8') as w:
            w.write('\n'.join(lines) + '\n')
        allout.extend(lines)
    print('file  rec  unk  opt  lines  chars')
    for s in stat:
        print('%-8s %5d %4d %4d %6d %7d' % s)
    print('TOTAL lines', len(allout), 'chars', sum(len(x) for x in allout))


if __name__ == '__main__':
    main()
