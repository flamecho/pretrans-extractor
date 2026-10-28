#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""私立ベルばら学園 ～ベルサイユのばらReimagination～ (NS) —— STCM2L 全文本提取

链路（2026-10-24 实证）:
  XCI --hactool -t xci--> secure/*.nca（4.87 GB 主 NCA）--hactool -t nca--> RomFS
      -> CONTENTS/STORY.cpk (CRI CPK) -> SCRIPT/*.DAT (STCM2L, UTF-8)

记录形状（L1 实证；全库 191 文件指令流零失步）:
  文件 = 'STCM2L <build date>' 头 + GLOBAL_DATA + 'CODE_START_' + 指令流（尾部 200-400B 收尾区）
  指令 = [u32 op][u32 argc][u32 size]（size 含实参，4 对齐）＋ argc × 12B 实参
  实参 = [u32 值/指针][f32 2.0][f32 2.0]；值为串节点指针时指向：
  串节点 = [u32 0][u32 样式号 2..21][u32 1][u32 L][UTF-8][NUL][补 0 到 L]，L = align4(bytelen+1)

op 语义（L0，全库计数见 --stats）:
  0x103A4 / 0x103C4     正文一段（＝框内一行显示）
  0x38A28 / 0x38A48     正文多段：argc=8 = [音声槽][行1..3] ＋ [音声槽][行1..3]；后半为互斥变体 ⇒ 取前半
  0x1F4                 一次点击 / 等待 ⇒ 框边界（全库 79,728 次）
  0x1E00 / 0x1E20       幕・場タイトル（扉文，收）
  0x10AA0 / 0x10AC0     名札（说话人，丢；无独立名字窗，故正文不加前缀）
  0x1163C / 0x1161C / 0x11680 / 0x116A0 / 0x116BC
                        选项（实参含 sureN 分支标签，首槽为选项文本）

成行: 一次点击 = 一个文本框 = 一行（框内各显示行合并）；选项一行一条按序；幕题各占一行。
主角名: `#NAME[1]` = 姓（可改），默认 山田；vndb v21785 "Yamada Oscar"，母 "Yamada Nobara"。
用法: python scripts/beru_extract.py <SCRIPT目录> <out.txt> [--stats]
"""
import sys, os, glob, re, struct

HERO = '山田'
TEXT = {0x103A4, 0x103C4}
MULTI = {0x38A28, 0x38A48}
CLICK = 0x1F4
TITLE = {0x1E00, 0x1E20}
NAME = {0x10AA0, 0x10AC0}
OPT = {0x1163C, 0x1161C, 0x11680, 0x116A0, 0x116BC}
RE_SURE = re.compile(r'^sure\d+$')
RE_NAME = re.compile(r'#NAME\[\d\]')
JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')


def node(d, p):
    """串节点：形状不符即返回 None（记录自定界，永不失步）"""
    n = len(d)
    if not (0 <= p < n - 16):
        return None
    z, t, one, L = struct.unpack_from('<4I', d, p)
    if z != 0 or one != 1 or L % 4 or not (4 <= L <= 4000) or p + 16 + L > n:
        return None
    body = d[p + 16:p + 16 + L]
    k = body.find(b'\x00')
    if k <= 0 or (k + 1 + 3) & ~3 != L or body[k + 1:].strip(b'\x00'):
        return None
    try:
        return body[:k].decode('utf-8')
    except UnicodeDecodeError:
        return None


def walk(d):
    i = d.find(b'CODE_START_')
    if i < 0:
        return []
    o, n, out = i + 16, len(d), []
    while o + 12 <= n:
        op, argc, ln = struct.unpack_from('<3I', d, o)
        if ln < 12 or ln % 4 or o + ln > n or argc > 64 or 12 + argc * 12 > ln:
            break
        args = [node(d, struct.unpack_from('<I', d, o + 12 + k * 12)[0]) for k in range(argc)]
        out.append((op, args, argc))
        o += ln
    return out


def clean(s):
    s = RE_NAME.sub(HERO, s)
    return ''.join(c for c in s if c >= ' ' or c == '\u3000')


def add(lst, s):
    s = clean(s)
    if s:
        lst.append(s)


def boxes(instrs):
    out, cur = [], []

    def flush():
        if cur:
            out.append(''.join(cur))
            cur.clear()

    for op, a, argc in instrs:
        if op in TEXT:
            if a[0]:
                add(cur, a[0])
        elif op in MULTI:
            g = a[1:4]
            if not any(x for x in g):
                g = a[0:3]
            for s in g:
                if s:
                    add(cur, s)
        elif op == CLICK:
            flush()
        elif op in TITLE:
            flush()
            if a and a[0]:
                add(out, a[0])
        elif op in OPT:
            txt = [s for s in a if s and not RE_SURE.match(s) and JP.search(s) and s not in ('e', 'd')]
            flush()
            if txt:
                add(out, txt[0])
    flush()
    return out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    stats = '--stats' in sys.argv
    files = sorted(glob.glob(os.path.join(src, '*.DAT')),
                   key=lambda p: int(re.sub(r'\D', '', os.path.basename(p)) or 0))
    rows = []
    for f in files:
        name = os.path.basename(f)[:-4]
        if name == 'init' or int(re.sub(r'\D', '', name) or 0) >= 10000:
            continue          # init/ 子目录另存；1xxxx = 章选择用幕题（与正编 0x1E00 同文，已收）
        d = open(f, 'rb').read()
        if not d.startswith(b'STCM2L'):
            continue
        b = boxes(walk(d))
        rows.append(b)
        if stats:
            print('%-8s %5d %s' % (name, len(b), (b[0][:40] if b else '')))
    if stats:
        print('TOTAL', sum(len(b) for b in rows))
        return
    lines = [t for b in rows for t in b]
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as o:
        o.write('\n'.join(lines) + '\n')
    print('lines', len(lines))


if __name__ == '__main__':
    main()
