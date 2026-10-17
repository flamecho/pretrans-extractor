#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""恋戦隊LOVE＆PEACE THE P.S.P. (PSP / BROCCOLI 2012) MES.DAT text extractor.

容器: PSP_GAME/USRDIR/MES.DAT
  [u32 n][u32 ver=3][n*u32 offset][(n-1)*u16 ?][commands]
  cmd start = 8 + 4n + 2(n-1) = 8+4n+2n-1
  各 .MES の実データ長 = 次の 96 バイトゼロ連の直前まで

文字コード: 各バイト +0x20 (& 0xFF) → cp932。0x0A は同ボックス内の軟改行。
命令長 (ELF 0xf420 の分派木より):
  op <= 0x2a          : 3 バイト (op + 2)
  0x2b <= op <= 0x51  : 1 + NUL終端文字列 + 1
  op >= 0x52          : 9 バイト
  0x4e..0x51          : 表示文字列 (0x4f=名札 / 0x50=本文 / 0x51=選択肢)
"""
import os
import re
import struct
import sys

MES = sys.argv[1] if len(sys.argv) > 1 else '_src_lovepeace/PSP_GAME/USRDIR/MES.DAT'
OUT = sys.argv[2] if len(sys.argv) > 2 else '提取结果/恋戦隊LOVE＆PEACE_全文本.txt'


def read_index(d):
    cnt = struct.unpack_from('<I', d, 0)[0]
    ents = []
    for i in range(cnt):
        o = 0x618 + i * 0x40
        nm = d[o + 4:o + 0x24].split(b'\0')[0].decode('latin1')
        off = struct.unpack_from('<I', d, o + 0x3c)[0]
        ents.append((nm, off))
    return ents


def extent(d, off, limit):
    """ブロックは [off, limit) ；実データは末尾のゼロ詰めを削った長さ"""
    end = limit
    while end > off and d[end - 1] == 0:
        end -= 1
    return end - off


def dec(s):
    return bytes((x + 0x20) & 0xFF for x in s).decode('cp932', 'replace')


def parse(seg, size, start):
    """yield (pos, op, arg) ; arg = str for string ops, bytes for others"""
    p = start
    while p < size - 2:
        if seg[p] == 0 and seg[p:p + 64] == b'\0' * 64:
            return  # 末尾パディング（以降にゴミ領域）
        op = seg[p]
        if op <= 0x2a:
            yield p, op, seg[p + 1:p + 3]
            p += 3
        elif op <= 0x51:
            j = seg.find(b'\x00', p + 1)
            if j < 0:
                return
            raw = seg[p + 1:j]
            yield p, op, dec(raw) if op >= 0x4e else raw.decode('latin1')
            p = j + 1
        else:
            yield p, op, seg[p + 1:p + 9]
            p += 9


# 主人公 正義 愛子（vndb c30143 / v8092 Protagonist）。$f=姓(正義) / $n=名(愛子)
RENAME = {'$f': '正義', '$n': '愛子'}
TAGS = ('@l',)  # 大文字表示タグ（上屏特効の演出マーカー）


def clean(t):
    for tag in TAGS:
        t = t.replace(tag, '')
    for k, v in RENAME.items():
        t = t.replace(k, v)
    # 注音ルビ ｛ヨミ／親文字｝ → 親文字（画面に出るのは親文字）
    t = re.sub('｛([^／｝]*)／([^｝]*)｝', r'\2', t)
    return t.replace('\n', '')


STORY_PREFIX = ('JPROLOGUE', 'J0')
SKIP = ('ADVMENU', 'AUTOSAVE', 'CG_', 'DB_', 'DBBIG', 'DBMOJI', 'DEBUG', 'LOAD',
        'LOG', 'MAIN', 'MANUAL', 'MC_INIT', 'MUSIC', 'NAMESET', 'OPTION', 'QLOAD',
        'QSAVE', 'RTITLE', 'SAVE', 'SC_END', 'SCE_', 'SHOP_MODE', 'START')


def main():
    d = open(MES, 'rb').read()
    ents = read_index(d)
    offs = {nm: off for nm, off in ents}
    order = [nm for nm, _ in ents]
    blocks = {}
    stats = []
    for i, nm in enumerate(order):
        if not nm.startswith(STORY_PREFIX):
            continue
        off = offs[nm]
        limit = offs[order[i + 1]] if i + 1 < len(order) else len(d)
        ex = extent(d, off, limit)
        seg = d[off:off + ex]
        try:
            n = struct.unpack_from('<I', seg, 0)[0]
            start = 8 + 4 * n + 2 * n - 1
            if not (0 < start < ex):
                raise ValueError
        except Exception:
            stats.append((nm, ex, 0, 0, 'HDR?', 0))
            continue
        lines = 0
        opts = 0
        buf = []
        for pos, op, arg in parse(seg, ex, start):
            if op == 0x50:
                t = clean(arg)
                if t.strip():
                    buf.append(t)
                    lines += 1
            elif op == 0x51:
                t = clean(arg)
                if t.strip():
                    buf.append(t)
                    opts += 1
        blocks[nm] = buf
        stats.append((nm, ex, start, lines, opts, ''))
    # 阅读順: JPROLOGUE1-5 → J01..J06（章→部）→ 各ルートの PSP 後日談
    def key(nm):
        core = nm[:-4] if nm.endswith('.MES') else nm
        m = re.match(r'JPROLOGUE(\d+)$', core)
        if m:
            return (0, int(m.group(1)), 0, 0)
        m = re.match(r'J(\d+)_PSP_', core)
        if m:
            return (1, int(m.group(1)), 99, 0)
        m = re.match(r'J(\d+)_(\d+)_(\d+)_(\d+)$', core)
        if m:
            return (1, int(m.group(1)), int(m.group(2)), int(m.group(3)) * 10 + int(m.group(4)))
        return (9, 0, 0, 0)
    out = []
    for nm in sorted(blocks, key=key):
        out.extend(blocks[nm])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(out) + '\n')
    tot = sum(s[3] for s in stats)
    opt = sum(s[4] for s in stats)
    print(f"files={len(stats)} textlines={tot} options={opt} -> {OUT}")
    for s in stats:
        if s[5] or s[3] == 0:
            print("  WARN", s)


if __name__ == '__main__':
    main()
