#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""宵闇 本体正文重建（源＝eden dump 的 merged romfs，即 v1.1.1 实际显示文本）。

为何要重建：原成品本体段取自 NSP v0 的 27 个池，经比对发现
  ① `static~90_01`（後日談会話）整池未收（33 行）
  ② `static~91_01` 缺 17 条角色後日談
  ③ 00–25 章约 150 行与 v1.1.1 不一致（例：`カークランド` → `カークライド`）

收录池（按显示顺序）：00_01 … 25_01 → 90_01 → 91_01
排除池：localize / summary / start / skill / script / still / image /
        clue / clueinfo / agenda / article / chapter / name / emotion / flag / flagsys / result（系统·UI·商品说明）

去重规则同 scripts/tempest_dlc_text.py（段行保留，合并行/定位变体/同文丢弃）。
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
IDLIKE = re.compile(r'^[0-9_]+(?:dlc)?$|^\d{4}_\d{4}$')
NAME = 'アナスタシア'


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
        if not t or IDLIKE.match(t) or t.startswith('//'):
            continue
        items.append((raw, t))

    n = len(items)
    drop = set()
    for i in range(n):
        t = items[i][1]
        for k in (2, 3):
            if i + k <= n - 1:
                join = ''.join(items[i + 1 + j][1] for j in range(k))
                if t == join:
                    drop.add(i)
                    break
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
    order = ['%02d_01' % i for i in range(26)] + ['90_01', '91_01']
    out = []
    for ch in order:
        p = os.path.join(DUMP, 'static~%s.bin.nx.bea' % ch)
        if not os.path.exists(p):
            print('  池 %s 缺文件' % ch)
            continue
        r = chapter(p)
        if r is None:
            print('  池 %s 解析失败' % ch)
            continue
        r = [x.replace('######', NAME) for x in r]
        out.extend(r)
        print('  池 %-6s %4d 行' % (ch, len(r)))
    print('\n本体合计 %d 行' % len(out))
    d = sys.argv[1] if len(sys.argv) > 1 else '_w_upd1_yaoi/base_text.txt'
    io.open(d, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    print('写入', d)


if __name__ == '__main__':
    main()
