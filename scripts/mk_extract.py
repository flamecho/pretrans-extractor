# -*- coding: utf-8 -*-
"""マール王国の人形姫（NS）文本提取器

【容器链】rhapsody.vfs (VFS3) → *.PAK
【脚本载体】TOWN2J.PAK（其余 PAK 为图形/UI/音声）
【记录形态 · L1 自定界】
  [u16 size_words][变长头(以 0x0002 结尾)][cp932 文本][NUL][pad]
  记录总长 = size_words * 2  ⇒ 用 size 直接跳下一条，永不失步。
  记录流连续铺满文本区；存在「空文本记录」（只有头，文本为空），必须照样跳过去，
  否则会重同步失步（实测会把 'う～ん、王子さま……。' 切成 'う～'）。
【文本内控制码】
  'R' (0x52) = 框内改行（单行恒 ≤19 全角字 = 窗口行宽）
  'J1'       = 主角名宏（游戏内另有「コルネット」字面 40 处 → 取之）
【断框判据 · L1 + 交叉验证（本作实证）】
  文本框恒为 3 行。「R 连跑(≥2)结束后，行号落在 3 行框首行」= 526/527 = 99.8%；
  对照 H=2 → 18.4%，H=4 → 1.5%，H=5 → 0.4%。
  ⇒ 每 3 个「行」= 一个文本框 = 一次点击 = 输出一行。
"""
import struct
import sys

SIZE_MIN = 4
BOX_LINES = 3
NAME_MACRO = 'J1'
NAME_DEFAULT = 'コルネット'
HDR_MAX = 40


def is_jp(t):
    if any('\uff61' <= c <= '\uff9f' for c in t):
        return False                      # 半角片假名 = 二进制区误配
    kana = sum(1 for c in t if '\u3040' <= c <= '\u30ff')
    if kana:
        return True
    # 纯记号行（如「…………。」）保留，单字孤立汉字丢弃
    return len(t) >= 2 and all('\u4e00' <= c <= '\u9fff'
                               or c in '、。「」！？…ー～―（）『』' for c in t)


def parse_rec(d, p, total):
    """返回记录文本；空文本记录返回 ''；结构不符返回 None。

    头布局：[u16 size][u16 A][u16 B][4B flags][k×u16]
    头内 u16 恒 < 0x2000（高字节 ≤0x1F），而 cp932 尾字节恒 ≥0x40
    ⇒ 从 p+10 起按 2 字节步进，直到「高字节 ≥0x40」处即正文起点。
    """
    end = p + total
    if end > len(d):
        return None
    if d[end - 1] != 0:
        return None
    i = end - 1
    while i > p and d[i] == 0:
        i -= 1
    if i <= p + 4:
        return ''
    z = i + 1
    # 头 = [size][A][B][flags 4B][k×u16]，u16 均含 0x00 或控制字节
    # ⇒ 从 p+10 起按 2 字节步进，第一个「能整段干净解码」的位置即正文起点
    # 头长公式（实测反推，见报告）：
    #   头 = [size][A][B][f0 f1 f2 f3][k×u16]
    #   k = 3 + f1 + (1 if f3 == 2 else 0)   ⇒ 头长 = 10 + 2k
    # 例：flags 01 02 01 01 → k=5 → 20B；01 03 01 02 → k=7 → 24B
    total = end - p
    f1 = d[p + 7]
    f3 = d[p + 9]
    hl = 10 + 2 * (3 + f1 + (1 if f3 == 2 else 0))
    if hl < total and d[p + hl - 1] == 0:      # 头末 u16 高字节必为 0
        try:
            t = d[p + hl:z].decode('cp932')
        except Exception:
            t = None
        if t is not None and not any(ord(c) < 0x20 for c in t):
            return t
    # 兜底：逐 2 字节找第一个干净解码位（优先全角开头）
    first = None
    q = p + 10
    for _ in range(16):
        if q + 1 >= z:
            break
        try:
            t = d[q:z].decode('cp932')
        except Exception:
            q += 2
            continue
        if t and not any(ord(c) < 0x20 for c in t):
            if first is None:
                first = t
            b0 = d[q]
            if 0x81 <= b0 <= 0x9F or 0xE0 <= b0 <= 0xFC or d[q:q + 2] == b'J1':
                return t
        q += 2
    if first is None and d[i] == 0x02 and d[i + 1] == 0:
        return ''          # 头以 0x0002 收尾、正文为空
    return first


def _rec(d, p):
    """p 处若为合法记录返回 (total, text)，否则 None。"""
    N = len(d)
    if p + 6 >= N:
        return None
    size = d[p] | (d[p + 1] << 8)
    if not (SIZE_MIN <= size <= 0x4000):
        return None
    total = size * 2
    if p + total > N or d[p + total - 1] != 0:
        return None
    t = parse_rec(d, p, total)
    if t is None:
        return None
    return total, t


def _try(d, p):
    """p 处若为合法记录返回 (total, text)。"""
    N = len(d)
    if p + 6 >= N:
        return None
    size = d[p] | (d[p + 1] << 8)
    if not (SIZE_MIN <= size <= 0x4000):
        return None
    total = size * 2
    if p + total > N or d[p + total - 1] != 0:
        return None
    t = parse_rec(d, p, total)
    if t is None:
        return None
    return total, t


def walk(d):
    """两路扫描后取并集，最大化覆盖：
    (a) 跳跃式：命中即按 size 跳（快，覆盖连续文本区）
    (b) 逐 2 字节：不漏任何起点（慢一些，但保证覆盖）
    最后统一做「连续成链」过滤，剔除二进制区孤立误配。"""
    N = len(d)
    found = {}

    p = 0
    while p + 6 < N:
        r = _try(d, p)
        if r:
            found[p] = r
            p += r[0]
        else:
            p += 2

    p = 0
    while p + 6 < N:
        r = _try(d, p)
        if r:
            found[p] = r
            p += 2                      # 逐点前进，保证不漏
        else:
            p += 2

    # 取「最长连续链」：真记录在正文区是首尾相接铺满的，误配只会孤立出现或
    # 跨越真记录。先按起点建图，找极大链，再丢弃与已选区间重叠的其余候选。
    starts = set(found)
    ends = {o + found[o][0] for o in found}
    # 极大链：从没有前驱的点出发
    chains = []
    for o in sorted(found):
        # 若 o 有前驱（某条记录正好结束在 o），则它不是链首
        has_pred = o in ends
        if has_pred:
            continue
        cur = []
        q = o
        while q in found:
            cur.append(q)
            q = q + found[q][0]
        if len(cur) >= 2:
            chains.append(cur)
    chains.sort(key=lambda c: -len(c))
    taken = []
    chosen = {}
    for c in chains:
        for q in c:
            r0, r1 = q, q + found[q][0]
            if any(not (r1 <= a0 or r0 >= a1) for a0, a1 in taken):
                continue
            taken.append((r0, r1))
            chosen[q] = found[q]
    for o in sorted(found):
        if o in chosen:
            continue
        r0, r1 = o, o + found[o][0]
        if any(not (r1 <= a0 or r0 >= a1) for a0, a1 in taken):
            continue
        txt = found[o][1]
        kana = sum(1 for ch in txt if '\u3040' <= ch <= '\u30ff')
        if kana >= 2 and not any('\uff61' <= ch <= '\uff9f' for ch in txt):
            taken.append((r0, r1))
            chosen[o] = found[o]
    return [(o, chosen[o][0], chosen[o][1]) for o in sorted(chosen)]


def split_boxes(text):
    """R = 改行；每 BOX_LINES 行 = 一个文本框（同框内改行合并）。"""
    lines = text.split('R')
    boxes = []
    for i in range(0, len(lines), BOX_LINES):
        chunk = lines[i:i + BOX_LINES]
        while chunk and chunk[-1] == '':
            chunk.pop()
        if not chunk:
            continue
        s2 = ''.join(chunk).strip()
        if s2:
            boxes.append(s2)
    return boxes


def main():
    pak, out = sys.argv[1], sys.argv[2]
    d = open(pak, 'rb').read()
    recs = walk(d)
    rows = []
    for off, total, t in recs:
        for b in split_boxes(t):
            if not is_jp(b):
                continue
            b = b.replace(NAME_MACRO, NAME_DEFAULT)
            # 头尾残留：个别记录头长判定偏短 2 字节，正文前会粘上 1-2 个 ASCII 字节
            # （实测 'z7…'/'@A…'/'{"…'/'d$…' 等 12 例）。真实正文不会以 ASCII 起头。
            k = 0
            while k < len(b) and ord(b[k]) < 0x80:
                k += 1
            if 0 < k < len(b):
                b = b[k:]
            if is_jp(b):
                rows.append(b)
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        for r in rows:
            f.write(r + '\n')
    print('records=%d lines=%d' % (len(recs), len(rows)))


if __name__ == '__main__':
    main()
