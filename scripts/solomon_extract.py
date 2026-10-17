#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[PSP-JP] Solomon's Ring ～地の章～  (Plan Peace / InterOne, ULJM06200系)
文本提取：data.dat (自定义 PAK) -> pct_mess.dat (消息池) -> 全文本

链路：
  1) .chd(CHD v5/zstd) --scripts/chd_to_iso.js--> ISO
  2) ISO: PSP_GAME/USRDIR/data.dat = 自定义归档
       [u32 offset][u32 size] * N   (表字节数 = u32[0]，N 逐作变：
        地/水の章 14592 项全满；緋の章 表 0x15000 仅填 10723 项，尾部 0xCD 填充)
  3) 归档内 entry#1 = 路径名表 (data/cmn/... , data/pct/e/pct_mess.dat ...)
     名字序号 i <-> 条目序号 i+10
  4) pct_mess.dat 结构：
       u32 n ; u32 pad ; u32 off[n] ; pool
       base = 8 + 4*n ; 段 k = pool[off[k-1] : off[k]]  (off[-1] = 0)
       每段 = 一个文本框（一次点击），段内 0x0A = 框内换行 → 合并
      cp932 明文，无控制码、无说话人标记
  5) 剔除开发用测试串（"波演出"/"選んだ"/"選択肢文N"/全角数字串）

用法：
  python scripts/solomon_extract.py <data.dat> <out.txt>
"""
import struct
import sys
import re
import io

NAME_DELTA = 10                # 名字序号 -> 条目序号
FILL = 0xCDCDCDCD              # 表尾未初始化填充（MSVC debug fill）

LEAD = set(range(0x81, 0xA0)) | set(range(0xE0, 0xFD))


def jp_ratio(b):
    n = 0
    i = 0
    L = len(b)
    while i < L:
        c = b[i]
        if c in LEAD and i + 1 < L and 0x40 <= b[i + 1] <= 0xFC and b[i + 1] != 0x7F:
            n += 1
            i += 2
        else:
            i += 1
    return n / max(L, 1)


def read_entries(d):
    """表头 u32[0] = 表字节数；表项可能未填满，尾部为 0xCDCDCDCD 或越界，
    以「首项越界即止」截断（地/水の章表满 14592 项，緋の章实为 10723 项）。"""
    hdr = struct.unpack_from('<I', d, 0)[0]
    ents = []
    for i in range(hdr // 8):
        o, s = struct.unpack_from('<II', d, i * 8)
        if o == FILL or s == FILL or o + s > len(d):
            break
        ents.append((o, s))
    return ents


def find_mess_entry(d, ent):
    """结构化定位 pct_mess.dat：唯一满足「n + 偏移表 + 单调 + 高日文率」的条目。"""
    best = None
    for idx, (o, s) in enumerate(ent):
        if s < 4096 or d[o:o + 4] == b'RIFF':
            continue
        n = struct.unpack_from('<I', d, o)[0]
        if not (8 < n < 200000):
            continue
        base = 8 + 4 * n
        if base + 64 >= s:
            continue
        first = struct.unpack_from('<I', d, o + 8)[0]
        last = struct.unpack_from('<I', d, o + 8 + 4 * (n - 1))[0]
        if not (0 <= first <= last <= s - base):
            continue
        r = jp_ratio(d[o + base:o + s])
        if r > 0.30 and (best is None or r > best[0]):
            best = (r, idx)
    return None if best is None else best[1]


def parse_mess(b):
    n = struct.unpack_from('<I', b, 0)[0]
    base = 8 + 4 * n
    pool = b[base:]
    bounds = [0] + [struct.unpack_from('<I', b, 8 + 4 * k)[0] for k in range(n)] + [len(pool)]
    segs = []
    for k in range(len(bounds) - 1):
        segs.append(pool[bounds[k]:bounds[k + 1]])
    return segs


NOISE = [
    re.compile(r'^[０-９]+を選んだ$'),      # 開発用：分岐先の記録
    re.compile(r'^選択肢文[０-９]+$'),      # 開発用：選択肢ダミー
    re.compile(r'^波演出(中)?$'),           # 開発用：エフェクト名
    re.compile(r'^[０-９\n]+$'),            # 開発用：全角数字テスト列
    # 開発用テストブロック内の見出し（無引用符の完全一致のみ。地の章 idx161 / 水の章 idx161）
    re.compile(r'^どうする？$'),
]


def is_noise(t):
    return any(p.match(t) for p in NOISE)


def merge_lines(t):
    """框内软换行合并；续行行首 U+3000 为显示缩进，剥掉后直接拼接。"""
    lines = t.split('\n')
    out = lines[0]
    for ln in lines[1:]:
        out += ln.lstrip('\u3000')
    return out.rstrip('\n')


def main():
    src, dst = sys.argv[1], sys.argv[2]
    d = open(src, 'rb').read()
    ent = read_entries(d)
    idx = find_mess_entry(d, ent)
    if idx is None:
        raise SystemExit('pct_mess.dat 未定位')
    o, s = ent[idx]
    segs = parse_mess(d[o:o + s])
    kept, dropped = [], []
    for seg in segs:
        t = seg.decode('cp932')
        t = t.replace('\r', '').strip('\x00')   # 池尾 3 字节补零会落在末段
        if is_noise(t):
            dropped.append(t)
            continue
        m = merge_lines(t)
        if m:
            kept.append(m)
    with io.open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        for line in kept:
            f.write(line + '\n')
    print(f'entry #{idx} segments={len(segs)} kept={len(kept)} dropped={len(dropped)}')
    for t in dropped:
        print('  drop:', repr(t[:40]))


if __name__ == '__main__':
    main()
