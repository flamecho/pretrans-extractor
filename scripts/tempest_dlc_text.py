#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""宵闇 DLC 正文提取（源＝eden 模拟器 Dump RomFS，update 已合并）。

背景：NSP 侧 Update v1.1.1 是 BKTR 坏包（桶表缺失），数据区不可解；
      改用模拟器 dump 的 merged romfs，池文件可直接读。
池结构：`.nx.bea` = SCNE 容器 → 单 zstd 帧 → `BIN_` 池
        （0x0C=N、0x18=字符串区 base、0x1C 起 N×u32 偏移；闭合 0x1C+N*4==base）

★ 池内同一句有多种「排版/揭示」变体，去重规则（顺序执行）：
   1) 规范化：去引擎转义、去全部换行、去首尾空白/全角空格
   2) 合并行写在段行**之后**：t == 前 2–4 条拼接 ⇒ 丢
   3) 合并行写在段行**之前**：t == 后 2–3 条拼接 ⇒ 丢
   4) 与最近 8 条同文 ⇒ 丢
   5) `\\n` 定位变体（raw 以换行开头且与前 3 条同头部）⇒ 丢
"""
import zstandard as zstd
import struct
import re
import io
import os
import sys

DUMP = r'<本地路径>'
JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
ESC = re.compile(r'\\[fcs][a-zA-Z0-9]{0,2}|_x000D_|[\x00-\x08\x0b\x0c\x0e-\x1f]')
IDLIKE = re.compile(r'^[0-9_]+dlc?$|^\d{4}_\d{4}$')


def pool(path):
    b = open(path, 'rb').read()
    i = b.find(b'\x28\xb5\x2f\xfd')
    if i < 0:
        return None
    d = zstd.ZstdDecompressor().decompressobj().decompress(b[i:])
    h = d.find(b'BIN_')
    if h < 0:
        return None
    n = struct.unpack_from('<I', d, h + 0x0C)[0]
    bs = struct.unpack_from('<I', d, h + 0x18)[0]
    if bs != 0x1C + n * 4:
        return None
    offs = struct.unpack_from('<%dI' % n, d, h + 0x1C)
    out = []
    for x in offs:
        s = h + bs + x
        e = d.find(b'\0', s)
        out.append(d[s:e].decode('utf-8', 'replace'))
    return out


def clean(t):
    t = ESC.sub('', t)
    return t.replace('\n', '').replace('\r', '').strip(' \u3000\t')


def chapter(path):
    lst = pool(path)
    if lst is None:
        return None
    items = []
    for raw in lst:
        if not (JP.search(raw) or re.search(r'[「『（]', raw) and re.search(r'[」』）]', raw) and not re.search(r'[A-Za-z]{4,}', raw)):
            continue
        t = clean(raw)
        if not t or IDLIKE.match(t):
            continue
        items.append((raw, t))

    n = len(items)
    # 3) 合并行在前：t == 后 2–3 条拼接
    drop = set()
    for i in range(n):
        t = items[i][1]
        for k in (2, 3):
            if i + k <= n - 1:
                join = ''.join(items[i + 1 + j][1] for j in range(k))
                if t == join:
                    drop.add(i)
                    break
            # 容错：合并行只是「以后一条开头、以下一条结尾」
            if len(t) > 8 and i + 2 <= n - 1 and t.startswith(items[i + 1][1]) and t.endswith(items[i + 2][1]) and len(t) > len(items[i + 1][1]):
                drop.add(i)
                break

    out = []
    seen = set()
    for i, (raw, t) in enumerate(items):
        if i in drop:
            continue
        if t in out[-8:]:
            continue
        # 纯标点短行（「……」这类反应框）在同一池内只留首次，避免同一句重复上百次
        if not JP.search(t) and len(t) <= 12 and t in seen:
            continue
        if not JP.search(t) and len(t) <= 12:
            seen.add(t)
        if raw.startswith('\n') and any(t[:12] == x[:12] for x in out[-3:]):
            continue
        merged = False
        for k in (2, 3, 4):
            if len(out) >= k and t == ''.join(out[-k:]):
                merged = True
                break
        if merged and len(t) > 8:
            continue
        out.append(t)
    return out


def main():
    out = []
    for ch in range(32):
        p = os.path.join(DUMP, 'static~%02d_01_dlc.bin.nx.bea' % ch)
        if not os.path.exists(p):
            print('  章 %02d_01  缺文件' % ch)
            continue
        r = chapter(p)
        if r is None:
            print('  章 %02d_01  池解析失败' % ch)
            continue
        out.extend(r)
        print('  章 %02d_01  %4d 行' % (ch, len(r)))
    dup = sum(1 for a, b in zip(out, out[1:]) if a == b)
    print('\n合计 %d 行｜相邻重复 %d' % (len(out), dup))
    d = sys.argv[1] if len(sys.argv) > 1 else '_w_upd1_yaoi/dlc_text.txt'
    io.open(d, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    print('写入', d)


if __name__ == '__main__':
    main()
