#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""テミラーナ国の強運姫と悲運騎士団 (NS, Unity/UTXT) → 全文本

正文载体：Data/StreamingAssets/uma_talk_2.bytes
  0x00 "UTXT" | 0x04 u32 ver=1 | 0x08 u32 常量 | 0x0C u32 表长
  表 0x10..表长-4 + "TEND"：varint(记录数) + 记录数×varint(记录字节长)
  正文 = 记录首尾相接的「字符索引流」：
    0x00            → 框内换行
    0x01..0x7F      → 字符表[b-1]
    0x81..0x9D + b2 → 字符表[(b1-0x81)*128 + (b2-1) + 128]
  字符表 = Data/sharedassets0.assets 里名为 `chartable` 的 TextAsset（4413 字，**含 \r\n 行分隔**
           一起参与编号；这正是 0x08 常量之外唯一能对上 max index 4410 的表）

选项：Data/StreamingAssets/AdvChoice.txt（UTF-8 BOM CSV，列 問/選択肢；一行一选项）
"""
import os
import re
import struct
import sys

import UnityPy

ROMFS = '_w_W3_temi/romfs'
OUT = '提取结果/[NS-JP]テミラーナ国の強運姫と悲運騎士団.txt'
COUNTRY = 'テミラーナ'


def load_chartable():
    env = UnityPy.load(os.path.join(ROMFS, 'Data/sharedassets0.assets'))
    for obj in env.objects:
        if obj.type.name == 'TextAsset':
            d = obj.read()
            if getattr(d, 'm_Name', '') == 'chartable':
                raw = d.m_Script if hasattr(d, 'm_Script') else d.m_Text
                if isinstance(raw, str):
                    raw = raw.encode('utf-8', 'surrogateescape')
                return raw.decode('utf-8')
    raise RuntimeError('chartable not found')


def read_utxt(path):
    d = open(path, 'rb').read()
    assert d[:4] == b'UTXT'
    tbl_end = struct.unpack_from('<I', d, 0x0C)[0]
    assert d[tbl_end - 4:tbl_end] == b'TEND'
    tbl = d[0x10:tbl_end - 4]
    vals = []
    v = 0
    for x in tbl:
        v = (v << 7) | (x & 0x7f)
        if not x & 0x80:
            vals.append(v)
            v = 0
    cnt = vals[0]
    lens = vals[1:1 + cnt]
    o = tbl_end
    out = []
    for L in lens:
        out.append(d[o:o + L])
        o += L
    return out


def make_decoder(T):
    def dec(buf):
        out = []
        i = 0
        n = len(buf)
        while i < n:
            b = buf[i]
            if b == 0:
                out.append('\n')
                i += 1
            elif b < 0x80:
                k = b - 1
                out.append(T[k] if 0 <= k < len(T) else '')
                i += 1
            else:
                k = (b - 0x81) * 128 + (buf[i + 1] - 1) + 128
                i += 2
                out.append(T[k] if 0 <= k < len(T) else '')
        return ''.join(out)
    return dec


def clean(s):
    s = s.replace('$$R', '')          # 注音/強調マーク（本体は内側）
    s = re.sub(r'\n[\u3000 ]?', '', s)  # 框内软换行 → 合并（连带行首缩进）
    s = s.replace('\r', '')
    s = s.replace('##', COUNTRY)      # ##＝国名（題名「テミラーナ国」＋「##聖騎士団」）
    return s.strip()


def norm(s):
    return re.sub(r'[\s\\　]', '', s)


def load_choices():
    p = os.path.join(ROMFS, 'Data/StreamingAssets/AdvChoice.txt')
    d = open(p, 'rb').read().decode('utf-8-sig')
    rows = [r for r in d.split('\r\n') if r]
    groups = []
    cur = None
    for r in rows[1:]:
        f = r.split(',')
        code = f[0].strip()
        q = f[1].strip() if len(f) > 1 else ''
        opt = f[2].strip() if len(f) > 2 else ''
        if code:
            cur = {'code': code, 'q': q, 'opts': []}
            groups.append(cur)
        if opt:
            cur['opts'].append(opt)
    return groups


def main():
    T = load_chartable()
    dec = make_decoder(T)
    recs = read_utxt(os.path.join(ROMFS, 'Data/StreamingAssets/uma_talk_2.bytes'))
    texts = [clean(dec(b)) for b in recs]
    texts = [t for t in texts if t]

    groups = load_choices()
    # 选项插到「問」文本之后（按规范化全文匹配）
    index = {}
    for i, t in enumerate(texts):
        index.setdefault(norm(t), i)
    placed, miss = 0, []
    ins = {}
    for g in groups:
        k = norm(g['q'])
        i = index.get(k)
        if i is None:
            miss.append(g)
            continue
        ins.setdefault(i, []).extend(g['opts'])
        placed += 1

    lines = []
    n_opt = 0
    for i, t in enumerate(texts):
        lines.append(t)
        for o in ins.get(i, []):
            lines.append(clean(o))
            n_opt += 1
    for g in miss:
        for o in g['opts']:
            lines.append(clean(o))
            n_opt += 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(lines) + '\n')
    print('消息 %d  选项组 %d（就地 %d / 未匹配 %d）  选项行 %d  总行 %d'
          % (len(texts), len(groups), placed, len(miss), n_opt, len(lines)))
    for g in miss[:5]:
        print('  未匹配:', g['code'], g['q'][:40])


if __name__ == '__main__':
    main()
