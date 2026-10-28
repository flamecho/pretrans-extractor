#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ミストニアの翅望 -The Lost Delight- —— Unity/UTXT 文本（与 テミラーナ 同引擎）。

载体：Data/StreamingAssets/uma_talk_2.bytes（UTXT，字符索引流）
字符表：Data/sharedassets0.assets 内 TextAsset `chartable`
编码：
  0x00            → 框内换行
  0x01..0x7F      → chartable[b-1]
  0x81..0x9D + b2 → chartable[(b1-0x81)*128 + (b2-1) + 128]
"""
import os, struct, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import UnityPy

ROMFS = '_w_W1_mist/out'
OUT = '提取结果/[NS-JP]ミストニアの翅望 -The Lost Delight-.txt'
SRC = os.path.join(ROMFS, 'uma_talk_2.bytes')


def load_chartable():
    env = UnityPy.load(os.path.join(ROMFS, 'sharedassets0.assets'))
    for obj in env.objects:
        if obj.type.name == 'TextAsset':
            d = obj.read()
            if getattr(d, 'm_Name', '') == 'chartable':
                raw = d.m_Script
                if isinstance(raw, str):
                    raw = raw.encode('utf-8', 'surrogateescape')
                return raw.decode('utf-8')
    raise RuntimeError('chartable not found')


def read_utxt(path):
    d = open(path, 'rb').read()
    assert d[:4] == b'UTXT', d[:4]
    tbl_end = struct.unpack_from('<I', d, 0x0C)[0]
    assert d[tbl_end - 4:tbl_end] == b'TEND'
    tbl = d[0x10:tbl_end - 4]
    vals, v = [], 0
    for x in tbl:
        v = (v << 7) | (x & 0x7f)
        if not x & 0x80:
            vals.append(v)
            v = 0
    cnt = vals[0]
    lens = vals[1:1 + cnt]
    o, out = tbl_end, []
    for L in lens:
        out.append(d[o:o + L])
        o += L
    return out


def make_decoder(T):
    def dec(buf):
        out, i, n = [], 0, len(buf)
        while i < n:
            b = buf[i]
            if b == 0:
                out.append('\n'); i += 1
            elif b < 0x80:
                k = b - 1
                out.append(T[k] if 0 <= k < len(T) else ''); i += 1
            else:
                k = (b - 0x81) * 128 + (buf[i + 1] - 1) + 128
                i += 2
                out.append(T[k] if 0 <= k < len(T) else '')
        return ''.join(out)
    return dec


def clean(s):
    s = s.replace('$$R', '')
    s = re.sub(r'\n[\u3000 ]?', '', s)
    return s.replace('\r', '').strip()


def main():
    T = load_chartable()
    dec = make_decoder(T)
    recs = read_utxt(SRC)
    texts = [t for t in (clean(dec(b)) for b in recs) if t]
    print('记录 %d / 成行 %d' % (len(recs), len(texts)))
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(texts) + '\n')
    for t in texts[:8]:
        print('  ', t[:60])


if __name__ == '__main__':
    main()
