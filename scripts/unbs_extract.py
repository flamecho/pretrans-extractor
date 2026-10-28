#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Un:BIRTHDAY SONG～愛を唄う死神～another record（PSV PCSG00912）剧本提取（本作专用）。

链路：pkg2zip -x <pkg> <zRIF>  →  psvpfsparser -i app/PCSG00912  →  dec/data/sn.bin
      sn.bin = [u32 解压尺寸] + LZSS（环 0x1000 / 起点 0xFEE / 8 token 一 flag）
      平铺 3,390,576 B = 276 段 chunk 头表（16B/条：[u32 off][u32 size][8B 0]，表尾 0x1140）
      chunk 0 头部为调试场景表（本編スタート／ファイル実行／実験場／ＣＥＲＯ…）⇒ 不收

记录（L0，逐条实测）：
  开框  4F 0D 00 <u16 flag=1⇒随后有名札>    4F 0A 00 <u16>
  名札  46 0D 00 <cp932> 00                 独立名字窗 ⇒ 整行丢弃（11,521 条）
  正文  45 FF FF <u16 seq> <cp932> 00       18,664 条（主；收尾固定 4A FF FF 6A FF FF FF FF 49）
        47 FF FF <u16 seq> <cp932> 00        1,143 条（叙述/追記；收尾不带 49）
        45 0A 00 <u16 seq> <cp932> 00           20 条（『』引用变体）
  收框  4A FF FF 6A FF FF FF FF
  清框  49 FF FF FF FF   ← A 类：换页（一次点击）
  等待  48 FF FF          ← B 类：不清框、正文继续加到同一框（585 处边界）
  选项  31 80 80 <u32 n> + n×（01 00 <u16 idx> 00 00 <u32 hash> <cp932> 00）
  不收  32 80 80 / 01 00 FF FF（调试场景表）、0x0F–0x2D/0x34/0x39/0x3F/0x44 等演出指令

成行：一次点击 = 一行；同一框内 B 类续写 ⇒ 只出「双版对照」（段行 A,B,C ＋ 合并行 ABC，
      单段框不重复）；%N = 框内软换行（删并）；名札不加前缀。

用法：python scripts/unbs_extract.py <sn.bin|sn.dec> <out.txt>
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


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
    except UnicodeDecodeError:
        return None


TEXT_OPS = (b'\x45\xff\xff', b'\x47\xff\xff', b'\x45\x0a\x00')


def collect(o):
    recs = []
    for pat in TEXT_OPS:
        pos = 0
        while True:
            i = o.find(pat, pos)
            if i < 0:
                break
            pos = i + 1
            s = i + 5
            e = o.find(b'\x00', s)
            if e < 0:
                continue
            t = dec(o[s:e])
            if t:
                recs.append((i, 'msg', t))
    pos = 0
    while True:
        i = o.find(b'\x31\x80\x80', pos)
        if i < 0:
            break
        pos = i + 3
        n = struct.unpack_from('<I', o, i + 3)[0]
        if not 0 < n <= 8:
            continue
        q = i + 7
        items = []
        for _ in range(n):
            s = q + 10
            e = o.find(b'\x00', s)
            if e < 0 or e - s > 200:
                items = []
                break
            t = dec(o[s:e])
            if not t:
                items = []
                break
            items.append((q, t))
            q = e + 1
        recs.extend((q, 'opt', t) for q, t in items)
    recs.sort(key=lambda r: r[0])
    return recs


def clean(t):
    return ''.join(c for c in t.replace('%N', '') if ord(c) >= 0x20).strip()


def build(o, recs):
    frames = []
    cur = []
    for off, kind, t in recs:
        if kind == 'opt':
            if cur:
                frames.append(('msg', [x[2] for x in cur]))
                cur = []
            frames.append(('opt', [t]))
            continue
        if cur and b'\x49\xff\xff\xff\xff' in o[cur[-1][0]:off]:
            frames.append(('msg', [x[2] for x in cur]))
            cur = []
        cur.append((off, kind, t))
    if cur:
        frames.append(('msg', [x[2] for x in cur]))
    return frames


def main():
    src, dst = sys.argv[1], sys.argv[2]
    o = load(src)
    recs = collect(o)
    frames = build(o, recs)

    rows = []
    n_multi = n_seg = 0
    for kind, segs in frames:
        segs = [s for s in (clean(x) for x in segs) if s]
        if not segs:
            continue
        if kind == 'opt':
            rows.append(segs[0])
            continue
        n_seg += len(segs)
        if len(segs) == 1:
            rows.append(segs[0])
        else:
            n_multi += 1
            rows.extend(segs)
            rows.append(''.join(segs))

    os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
    open(dst, 'w', encoding='utf-8-sig', newline='\n').write('\n'.join(rows) + '\n')
    n_opt = sum(1 for k, s in frames if k == 'opt')
    print('平铺 %d B ｜ 记录 %d ｜ 正文段 %d ｜ 正文框 %d ｜ 多段框 %d ｜ 选项 %d ｜ 输出行 %d'
          % (len(o), len(recs), n_seg, len(frames) - n_opt, n_multi, n_opt, len(rows)))


if __name__ == '__main__':
    main()
