#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""うたの☆プリンスさまっ♪ Repeat LOVE (NS 010024200E00A000) 剧本提取。

链路: romfs/sn.bin → LZSS(0x1000 环 / 0xFEE 起点 / 首 4B=解压尺寸) → 平铺 → 本脚本

引擎与 All Star / After Secret 同族（CRI CPK + sn.bin LZSS），记录格式实测同构：
  开框      : 4F 0D 00 <flag u16>
  flag=1    : 46 0D 00 <名札> NUL          （名札不进正文；本作名札常带 %C999 前缀）
  正文      : 45 FF FF <idx u16> <cp932 文本> NUL
  收框      : 4A FF FF 6A FF FF FF FF 49 FF FF FF FF   ← L0：一次点击＝一行
  空框      : 4F 0D 00 xx 00 后面直接跟别的 op（无 45 FF FF）⇒ 不是正文

控制码：%N = 框内软换行（删，合并进同一行）｜%Z / %YE / %Y = 样式前缀（删）
占位符：●●● = 姓｜○○○ = 名｜●●● ○○○ = 全名（cp932 819C / 819B）

用法: python scripts/utapri_rl_ns_extract.py <sn.bin> <out.txt> [姓] [名]
"""
import os
import sys

SURNAME = '七海'
GIVEN = '春歌'


def lzss(src, size, start=4, wstart=0xFEE):
    """0x1000 环 / pos 起点 0xFEE / flag 每 8 token（LSB 优先，1=literal）。"""
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
            flags >>= 1
    return bytes(out)


def load(path):
    d = open(path, 'rb').read()
    if path.lower().endswith('.dec'):
        return d
    return lzss(d, int.from_bytes(d[:4], 'little', signed=True))


def dec(seg):
    try:
        return seg.decode('cp932')
    except Exception:
        return None


def strip_codes(t, sur, giv):
    """只剥控制码/占位符，不判内容（判内容交给调用方）。"""
    t = t.replace('●●● ○○○', sur + giv)
    t = t.replace('●●●', sur)
    t = t.replace('○○○', giv)
    t = t.replace('%N', '')                    # 框内软换行 ⇒ 合并进同一行
    t = t.replace('%Z', '')                    # 样式前缀
    t = t.replace('%C999', '')                 # 名札色码
    while t.startswith('%YE') or t.startswith('%Y'):
        t = t[3:] if t.startswith('%YE') else t[2:]
    t = ''.join(c for c in t if ord(c) >= 0x20)
    return t.strip()


def has_script(t):
    """是否含假名/汉字 —— 仅用于**标定剧本区起点**，不当成行的过滤条件。"""
    return any(0x3040 <= ord(c) <= 0x30FF or 0x4E00 <= ord(c) <= 0x9FFF for c in t)


ANCHOR = b'\x45\xff\xff'
NAMETAG = b'\x46\x0d\x00'
CLOSE = b'\x4a\xff\xff\x6a'


def scan(o):
    """收集所有「4F0D 开框 + 45FFFF 锚点」候选。

    ★ 两条实测坑：
      ① flag=1 不保证紧跟 46 0D 00 —— 9 处中间夹了 `44 00 00 ..` / `10 xx xx ..`，
         故名札要在 24 B 窗口内找；找不到就按无名札处理。
      ② 正文可能是**纯标点**（`「…………」`）或全角英文标题（`『ｍｙ sound never end』`），
         不能用「含假名/汉字」过滤，否则静默丢 117 条。
    """
    cand, names = [], []
    p, n = 0, len(o)
    while True:
        j = o.find(b'\x4f\x0d\x00', p)
        if j < 0:
            break
        flag = int.from_bytes(o[j + 3:j + 5], 'little')
        q = j + 5
        if flag == 1:
            k2 = o.find(NAMETAG, q, min(q + 24, n))
            if k2 >= 0:
                e = o.find(b'\x00', k2 + 3)
                if e < 0:
                    break
                nm = o[k2 + 3:e].decode('cp932', 'replace')
                if nm:
                    names.append(nm.replace('%C999', '').strip())
                q = e + 1
        k = o.find(ANCHOR, q, min(q + 48, n))
        if k < 0:
            p = j + 3
            continue
        t0 = k + 5
        e2 = o.find(b'\x00', t0, min(t0 + 700, n))
        if e2 < 0:
            p = j + 3
            continue
        t = dec(o[t0:e2])
        if not t:
            p = j + 3
            continue
        cand.append((t0, t, o[e2 + 1:e2 + 5] == CLOSE))
        p = e2 + 1
    return cand, names


def parse(o, sur, giv):
    cand, names = scan(o)
    # 剧本区起点 ＝ 第一条「带收框且含假名/汉字」的记录；其前是头表 / 场景选择菜单
    anchor = [c for c in cand if c[2] and has_script(c[1])]
    start = min(c[0] for c in anchor) if anchor else 0
    lines = []
    for off, t, _ in cand:
        if off < start:
            continue
        x = strip_codes(t, sur, giv)
        if x:
            lines.append(x)
    return lines, names


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    sur = sys.argv[3] if len(sys.argv) > 3 else SURNAME
    giv = sys.argv[4] if len(sys.argv) > 4 else GIVEN
    o = load(sys.argv[1])
    print(f'平铺 {len(o):,} B')
    lines, names = parse(o, sur, giv)
    out = [x for x in lines if x]
    os.makedirs(os.path.dirname(sys.argv[2]) or '.', exist_ok=True)
    with open(sys.argv[2], 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(out) + '\n')
    print(f'-> {len(out)} 行 / {sum(len(x) for x in out):,} 字 / 名札 {len(set(names))} 种')
    print('名札:', '、'.join(sorted(set(names))[:20]))


if __name__ == '__main__':
    sys.exit(main())
