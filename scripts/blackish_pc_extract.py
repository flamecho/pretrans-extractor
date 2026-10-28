#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[PC-JP] Blackish House sideA→（honeybee black 2016 / PC）
全文本提取 —— ASGARD 自研「AdvHD(ws2) 字节码」链路（与 NS 版 Unity+UTAGE 完全不同代）。

容器链（本作实测）：
  ISO9660 直读（scripts/iso9660.py，不落整盘）→ RIO.ARC（6,961,191 B，407 × *.ws2）
                        → SCRIPT.ARC（354,787 B，4 个 Lua 5.1 引擎库，无正文）

RIO.ARC 索引（ASGARD arc，与 DYC feat.apple-polisher 同构）：
  u32 count(408) | u32 hdr04(=表尾-0x10) | u32 size0 | u32 0
  count 条 [name UTF-16LE NUL]，前 count-1 条各跟 [u32 size_{i+1}][u32 end_i]
  第 i 个文件 = [end_{i-1}, end_i)，end_{-1}=0，size_0 取 header@0x08
  自证：Σsize == len − 数据区首（6,951,327 == 6,951,327，零误差）

加密：ws2 每字节 rotl_8(c,6)（解密等价 rotr 2）。

字节码（文本相关，L0）：
  0x14 <u16 cmdid> 00 00 "char" 00 <cp932 台词> 00   ← 一条 = 一个文本框 = 一次点击
  0x15 "%LC<名前>" 00 / 0x15 00 00                     ← 名札（独立名字窗）设置/清除，丢弃
  0x0F <n>  选项块：每项 <u16 cmdid><cp932 选项文>00 00 <u8 jid> 00 07 <目标脚本>00

成行判据（L0）：35,142 条文本指令 **每条恰好 1 个 %K**（等待点击）——`Counter({1: 35142})`，
0 条无 %K、0 条多 %K ⇒ 一指令＝一点击，无「同框第二文本指令」⇒ **单版**。
`%P`（清框）34,899 条；缺 %P 的 243 条＝絵本 BA_ehon 等「不清框」页（与 NS 的 BrPage 对应），仍是一指令一点击。

用法: python scripts/blackish_pc_extract.py [--arc _work_bhpc/RIO.ARC] [--out ...] [--stats]
"""
import argparse
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import struct

HOME = os.environ.get('VNTRANS_HOME', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(HOME, '_work_bhpc/RIO.ARC')
OUT = os.path.join(HOME, '提取结果/[PC-JP] Blackish House sideA→.txt')

# 主角（可改名，默认名；vndb v17853 与本作 NS 版一致）
NAME_FIRST = '雛'
NAME_FAMILY = '亜麻乃'
MACROS = {'<@FIRNAME>': NAME_FIRST, '<@FAMNAME>': NAME_FAMILY}

ROUTES = ['BAkyo', 'BArei', 'BAtou', 'BAgou', 'BAmad']
TAIL = ['BA_omake01', 'BA_omake02', 'BA_omake03', 'BA_omake04']
LAST = ['BA_ehon']

TEXT = re.compile(rb'\x14(.{4})char\x00([^\x00]*)\x00', re.S)
CODE = re.compile(r'%XS\d*|%XE|%CF[0-9A-F]{3}|%LC|%K|%P')
RUBY = re.compile(r'\{([^{}:：\s]+)[:：][^{}]*\}')


def rot(b):
    return bytes((((c << 6) | (c >> 2)) & 0xFF) for c in b)


def parse_arc(d):
    cnt, _h4, size0, _z = struct.unpack_from('<IIII', d, 0)
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
    cur = o
    assert sum(sizes) == len(d) - cur, (sum(sizes), len(d) - cur)
    out = {}
    for nm, sz in zip(names, sizes):
        out[nm] = rot(d[cur:cur + sz])
        cur += sz
    return out


def natkey(nm):
    m = re.match(r'^(.*?)(\d+)([a-z]*)$', nm)
    if not m:
        return (9999, '', nm)
    return (int(m.group(2)), m.group(3), nm)


def order(names):
    have = set(n[:-4] for n in names if n.endswith('.ws2'))
    seq = []
    for r in ROUTES:
        seq += sorted([b for b in have if b.startswith(r + '_')], key=natkey)
    seq += [b for b in TAIL if b in have]
    seq += [b for b in LAST if b in have]
    return seq


def scan_select(t):
    """选项块：0x0F <n>，逐项 <u16>text 00 00 <u8 jid> 00 07 <target> 00。
    自证：118 项的目标脚本全部存在于 RIO.ARC 名表。"""
    out = []
    for m in re.finditer(rb'\x0f([\x02-\x08])', t):
        p = m.start()
        n = t[m.start() + 1]
        q = p + 2
        items = []
        for _ in range(n):
            if q + 2 > len(t):
                break
            q += 2                                   # u16 cmdid
            e = t.find(b'\x00', q)
            if e < 0 or e - q > 300 or e == q or t[e:e + 4] == b'\x00\x00\x00\x00':
                break
            try:
                txt = t[q:e].decode('cp932')
            except UnicodeDecodeError:
                break
            q = e + 1
            if t[q] != 0x00 or t[q + 2] != 0x00 or t[q + 3] != 0x07:
                break
            q += 4
            e2 = t.find(b'\x00', q)
            if e2 < 0:
                break
            tgt = t[q:e2].decode('latin1')
            q = e2 + 1
            items.append((txt, tgt))
        if len(items) == n:
            out.append((p, items))
    return out


def clean(t):
    t = t.replace('\\n\u3000', '').replace('\\n', '')   # 框内软换行（字面 \n＋缩进）
    t = RUBY.sub(r'\1', t)                              # {漢字:よみ} → 漢字
    t = CODE.sub('', t)
    for k, v in MACROS.items():
        t = t.replace(k, v)
    return t.strip('\u3000 ').strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arc', default=SRC)
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--stats', action='store_true')
    a = ap.parse_args()

    files = parse_arc(open(a.arc, 'rb').read())
    seq = order(files)
    base = set(n[:-4].upper() for n in files)

    lines, per, opt_total, bad_tgt, dropped = [], [], 0, 0, 0
    for b in seq:
        t = files[b + '.ws2']
        ev = [(m.start(), 'T', m.group(2)) for m in TEXT.finditer(t)]
        for off, items in scan_select(t):
            ev.append((off, 'S', items))
        ev.sort(key=lambda x: x[0])
        n_t = n_o = 0
        for off, kind, payload in ev:
            if kind == 'T':
                s = clean(payload.decode('cp932', 'replace'))
                if not s:
                    dropped += 1
                    continue
                lines.append(s)
                n_t += 1
            else:
                for txt, tgt in payload:
                    if tgt.upper() not in base:
                        bad_tgt += 1
                        continue
                    s = clean(txt)
                    if s:
                        lines.append(s)
                        n_o += 1
                        opt_total += 1
        per.append((b, n_t, n_o))

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')

    if a.stats:
        print('scripts %d   texts %d   options %d   lines %d'
              % (len(seq), sum(p[1] for p in per), opt_total, len(lines)))
        print('选项目标非法 %d   空文本丢弃 %d' % (bad_tgt, dropped))
        print('选项块数 %d' % sum(1 for b in seq if any(True for _ in scan_select(files[b + '.ws2']))))
        for p in per:
            if p[2]:
                print('  opt', p)
    print('->', a.out, len(lines), '行')


if __name__ == '__main__':
    main()
