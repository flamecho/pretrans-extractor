#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Cendrillon palikA (NS) —— STCM2L 全文本提取

链路: XCI → hactool -t nca --romfsdir → CONTENTS/STORY_01.cpk (CRI CPK) → SCRIPT/*.DAT (STCM2L, UTF-8)
指令: [u32 op][u32 argc][u32 len][argc*3 u32 槽][内联串区]
串记录: [u32 0][u32 L/4][u32 1][u32 L][utf8][pad]；槽[0] = 串记录绝对偏移（L0）
op: 0xE340 正文1行 / 0x3B78C 正文多行(3槽×2份) / 0x3BB24・0x54B4C 正文变体
    0xEB4C 名札(丢) / 0x1F4 推奨＝一次点击(框末) / 选项=末槽 sureN 且首槽为日文
成行: 一次点击 = 一个文本框 = 一行；框内多行合并；选项各占一行。
用法: python scripts/cend_extract.py <SCRIPT目录> <out.txt> [--stats]
"""
import sys, os, glob, struct, re, collections

A4 = lambda n: (n + 3) & ~3
WAIT, NAME = 0x1F4, 0xEB4C
TEXT_OPS = (0xE340, 0x3B78C, 0x3BB24, 0x54B4C)
TITLE = 0x1DDC
HERO = '玻ヰ璃'
RE_SURE = re.compile(r'^sure\d+$')
RE_NAME = re.compile(r'#Name\[1\]')
RE_STYLE = re.compile(r'#(?:Color|Ruby|Size|Font|Bold|Italic)\[[^\]]*\]')
JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')


def readrec(d, off):
    """串记录两种头：[0][L/4][1][L] 16B ／ [L/4][1][L] 12B（指针指向头首）。"""
    if off < 0 or off + 16 > len(d) or off % 4:
        return None
    a, l4, one, L = struct.unpack_from('<4I', d, off)
    if a == 0 and one == 1 and L == l4 * 4:
        body = off + 16
    else:
        l4, one, L = struct.unpack_from('<3I', d, off)
        if one != 1 or L != l4 * 4:
            return None
        body = off + 12
    if not (4 <= L <= 8000) or body + L > len(d):
        return None
    raw = d[body:body + L]
    z = raw.find(b'\x00')
    if z < 0:
        z = len(raw)
    t = raw[:z]
    if raw[z:].strip(b'\x00'):        # NUL 之后必须全是 0 填充
        return None
    try:
        s = t.decode('utf-8')
    except Exception:
        return None
    r = ''.join(c for c in s if ord(c) >= 0x20 or c == '\n')
    return r or None


def walk(d):
    i = d.find(b'CODE_START_')
    if i < 0:
        return []
    o, n, out = i + 16, len(d), []
    while o + 12 <= n:
        op, argc, ln = struct.unpack_from('<3I', d, o)
        if ln < 12 or ln % 4 or o + ln > n or argc > 64 or 12 + argc * 12 > ln:
            break
        args = struct.unpack_from('<%dI' % (argc * 3), d, o + 12) if argc else ()
        ss = [readrec(d, args[k * 3]) for k in range(argc)]
        out.append((op, ss))              # 保留槽位（None 占位），供多行型对半切
        o += ln
    return out


def clean(s):
    s = RE_NAME.sub(HERO, s)
    s = RE_STYLE.sub('', s)
    return s.replace('\n', '').replace('\r', '').replace('\t', '')


def boxes(instrs):
    """产出 ('text', str) / ('opt', str)。"""
    out, cur = [], []
    for op, ss in instrs:
        if op in TEXT_OPS:
            if op == 0xE340:
                txt = [s for s in ss if s and s.strip()]
            else:
                # 多行型：arg＝[音声ID][行1..行n] ／ [音声ID][行1..行n]
                # 两半为互斥变体（名前入り版 / 名前なし版）⇒ 只取前一半，丢标记槽
                h = len(ss) // 2
                txt = [s for s in ss[1:h] if s and s.strip()]   # ss 为等长槽位
            for s in txt:
                cur.append(clean(s))
        elif op == WAIT:
            if cur:
                out.append(('text', ''.join(cur)))
                cur = []
        elif op == TITLE:
            body = [s for s in ss if s and s.strip()]
            if body:
                if cur:
                    out.append(('text', ''.join(cur)))
                    cur = []
                out.append(('text', clean(body[0])))
        else:
            lab = [s for s in ss if s and RE_SURE.match(s)]
            if lab and ss and ss[0] and JP.search(ss[0]):
                if cur:
                    out.append(('text', ''.join(cur)))
                    cur = []
                out.append(('opt', clean(ss[0])))
    if cur:
        out.append(('text', ''.join(cur)))
    return out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    stats_mode = '--stats' in sys.argv
    SKIP = {'9900', '9901'}          # 调试テストメニュー
    files = sorted(glob.glob(os.path.join(src, '*.DAT')), key=lambda p: int(re.sub(r'\D', '', os.path.basename(p)) or 0))
    files = [f for f in files if os.path.basename(f)[:-4] not in SKIP]
    rows, tot = [], 0
    for f in files:
        name = os.path.basename(f)[:-4]
        try:
            d = open(f, 'rb').read()
        except PermissionError:
            d = open('_work_cend/s9010.bin', 'rb').read()
        if not d.startswith(b'STCM2L'):
            continue
        ins = walk(d)
        b = boxes(ins)
        ntext = sum(1 for k, _ in b if k == 'text')
        nopt = sum(1 for k, _ in b if k == 'opt')
        if stats_mode:
            first = next((t for k, t in b if k == 'text'), '')
            print('%s txt=%4d opt=%3d %s' % (name, ntext, nopt, first[:46]))
        rows.append((name, b))
        tot += ntext + nopt
    if stats_mode:
        print('TOTAL', tot)
        return
    lines = []
    for name, b in rows:
        lines += [t for _, t in b]
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as o:
        o.write('\n'.join(lines) + '\n')
    print('lines', len(lines))


if __name__ == '__main__':
    main()
