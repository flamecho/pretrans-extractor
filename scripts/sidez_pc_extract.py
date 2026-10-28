#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[PC-JP] Blackish House ←sideZ（ASGARD AdvHD / .ws2 字节码）全文本提取。

链路（全部直读 ISO，不落整盘）：
  ISO9660 → Script.arc / Rio.arc / RIO2.ARC / RIO3.ARC
  arc 索引：u32 count | u32 table_len | u32 size0 | u32 0
            [name UTF-16LE NUL] × count（前 count-1 条各跟 [u32 size_{i+1}][u32 end_i]）
  ws2 解密：每字节 rotl_8(c,6)
  正文指令：14 <u32 id> "char\0" <cp932 台词\0>   （空串/非 char 字段＝送り命令，不收）
  名札指令：15 "%LC<名前>\0"                      （独立名字窗，整条丢弃）
  选项指令：0f <n> 后接 n 项 [u16 id][文本\0][3B][07 <跳转脚本\0>]
"""
import argparse
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import struct
import sys

HOME = os.environ.get('VNTRANS_HOME', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

NAME_FIRST = '雛'
NAME_FAMILY = '亜麻乃'
MACROS = {'<@FIRNAME>': NAME_FIRST, '<@FAMNAME>': NAME_FAMILY}

ORDER = ['BZep', 'BZkyo_', 'BZhal_', 'BZnoa_', 'BZnay_', 'BZser_', 'BZ_ehon', 'BZ_omake', 'BZ_thanks', 'BA_thanks']

TEXT = re.compile(rb'\x14(.{4})char\x00([^\x00]*)\x00', re.S)
XRUBY = re.compile(r'\{([^{}:：="\'\s]+)[:：][^{}]*\}')
JP = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]')
SCR = re.compile(r'^[A-Z0-9_]+$')


def rot(b):
    return bytes((((c << 6) | (c >> 2)) & 0xFF) for c in b)


def parse_arc(d):
    cnt, _tl, size0, _z = struct.unpack_from('<IIII', d, 0)
    o = 0x10
    names, pairs = [], []
    for i in range(cnt):
        s = o
        while d[o:o + 2] != b'\x00\x00':
            o += 2
        names.append(d[s:o].decode('utf-16le'))
        o += 2
        if i < cnt - 1:
            a, b = struct.unpack_from('<II', d, o)
            o += 8
            pairs.append((a, b))
    sizes = [size0] + [a for a, b in pairs]
    ends = [b for a, b in pairs]
    data = o
    assert sum(sizes) == len(d) - data, (sum(sizes), len(d) - data)
    out, cur = {}, data
    for nm, sz in zip(names, sizes):
        out[nm] = rot(d[cur:cur + sz])
        cur += sz
    return out


def natkey(b):
    m = re.match(r'^(.*?)(\d+)([a-z]*)$', b)
    if not m:
        return (9999, '', b)
    return (int(m.group(2)), m.group(3), b)


def order_key(b):
    for i, p in enumerate(ORDER):
        if b.startswith(p):
            if p == 'BZep':
                return (i, natkey(b), b)
            return (i, natkey(b), b)
    return (999, natkey(b), b)


def clean(t):
    t = re.sub(r'%[A-Z]{1,3}', '', t)              # %K %P %LC %LR %XS %XE
    t = re.sub(r'[\ue000-\uf8ff]', '', t)          # PUA 内联图标
    t = XRUBY.sub(r'\1', t)                        # {漢字:かな} → 漢字
    t = re.sub(r'\\n[\u3000 ]?', '', t)            # 框内软换行
    for k, v in MACROS.items():
        t = t.replace(k, v)
    return t.strip('\u3000 \t')


def parse_choices(b):
    """返回 [(pos, [line, ...]), ...]；0f <n> + n×[u16 id][文本\\0][3B][07 <脚本>\\0]"""
    out, i, n = [], 0, len(b)
    spans = [(m.start(), m.end()) for m in TEXT.finditer(b)]

    def inside(p):
        for s, e in spans:
            if s <= p < e:
                return True
        return False

    while True:
        i = b.find(b'\x0f', i)
        if i < 0 or i + 2 > n:
            break
        cnt = b[i + 1]
        if not 1 <= cnt <= 8 or inside(i):
            i += 1
            continue
        p, items, ok = i + 2, [], True
        for _ in range(cnt):
            if p + 3 > n:
                ok = False
                break
            p += 2
            j = b.find(b'\x00', p)
            if j < 0:
                ok = False
                break
            try:
                t = b[p:j].decode('cp932')
            except UnicodeDecodeError:
                ok = False
                break
            if len(t) > 160 or any(ord(c) < 0x20 for c in t):
                ok = False
                break
            p = j + 4
            if p >= n or b[p] != 0x07:
                ok = False
                break
            j = b.find(b'\x00', p)
            if j < 0:
                ok = False
                break
            try:
                sc = b[p + 1:j].decode('ascii')
            except UnicodeDecodeError:
                ok = False
                break
            if not SCR.match(sc):
                ok = False
                break
            p = j + 1
            items.append(t)
        if ok and all(it.strip() for it in items):
            out.append((i, items))
            i = p
        else:
            i += 1
    return out


def extract(files, seq):
    lines, stats = [], []
    for base in seq:
        b = files[base + '.ws2']
        events = []
        for m in TEXT.finditer(b):
            t = clean(m.group(2).decode('cp932', 'replace'))
            if t:
                events.append((m.start(), 'T', [t]))
        for pos, items in parse_choices(b):
            cs = [clean(x) for x in items]
            cs = [x for x in cs if x]
            if cs:
                events.append((pos, 'C', cs))
        events.sort(key=lambda e: e[0])
        n_txt = n_ch = 0
        for _, kind, vals in events:
            for v in vals:
                lines.append(v)
            if kind == 'T':
                n_txt += 1
            else:
                n_ch += len(vals)
        stats.append((base, n_txt, n_ch))
    return lines, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default=os.path.join(HOME, '_work_sidez_pc/x'))
    ap.add_argument('--out', default=os.path.join(HOME, '提取结果/[PC-JP]Blackish House ←sideZ.txt'))
    ap.add_argument('--stats', action='store_true')
    a = ap.parse_args()

    files = {}
    for arc in ['Rio.arc', 'RIO2.ARC', 'RIO3.ARC']:
        files.update(parse_arc(open(os.path.join(a.dir, arc), 'rb').read()))

    names = [n[:-4] for n in files if n.endswith('.ws2')]
    seq = sorted([n for n in names if order_key(n)[0] < 999], key=order_key)
    skipped = sorted(n for n in names if order_key(n)[0] == 999)

    lines, stats = extract(files, seq)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')

    if a.stats:
        print('脚本 %d（收录）／跳过 %d' % (len(seq), len(skipped)))
        print('跳过:', ' '.join(skipped))
        print('正文 %d ／ 选项 %d ／ 合计 %d' % (
            sum(s[1] for s in stats), sum(s[2] for s in stats), len(lines)))
        for base, t, c in stats:
            if c:
                print('  选项 %-14s %d' % (base, c))
    print('->', a.out, len(lines), '行')


if __name__ == '__main__':
    main()
