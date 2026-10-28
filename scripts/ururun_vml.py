#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""うるるんクエスト 恋遊記 (PS2-JP / D3PUBLISHER, SLPM_660.28)
VML 剧本解析器 —— 同族：ラスト・エスコート（D3P PS2 FPK + VML）

容器：DATA/ADV.FPK（FPK 归档，与 DATA2/ 版同构）
  头：u32 count / u32 0 / u64 数据区总长 / u32 0x20 / u32 dataStart
  条目 32B：name[16] + u32 size + u32 offset + u64 pad
脚本：*.VML
  头：u32 hdrSize(0x10) / u32 tableOff / u32 count / u32 fileSize
  编码：JIS X 0208 的 7bit 形态（每字节 +0x80 = EUC-JP）

记录
  68 00 00 FF <u8 len> <len>           正文（1 记录 = 画面 1 行，≤18 字）
  64 00 00 FF <u8 len> <len>           名札（独立名字窗）
  F6 01 00 FF <u16 idx> <u8 len> <len> 选项

边界（L0）
  69 00 00 FF  同框软换行 → 合并
  6C 00 00 FF  直接接续（无换行）→ 合并
  6A / 6B      插入主角姓 / 名 → 行内替换（本作「姓」无取值，见下）
  66/67 00 00 FF 枠开始 → 断框（本作信件页之间只用 6C，必须靠它分页）
  其他         换框 → 断行
"""
import os
import re
import sys
import glob

NAME = '明里'
# 6A＝姓宏（同族 ラスト・エスコート 已证 6A=姓／6B=名）。本作仅 8 处，全在书院长信抬头
# 「[6A]　[6B]へ「…」」；盘内只有 1 个名字默认值「瑠璃」（16B 槽 @0x14C870，供 6B），
# 姓槽无初值 ⇒ 渲染为空串（8 处字节完全相同，不可能各不相同）。
SURNAME = ''

BREAK = (b'\x66\x00\x00\xff', b'\x67\x00\x00\xff')
SPACE = '\u3000'


def jp(b):
    try:
        return bytes(x + 0x80 for x in b).decode('euc_jp')
    except Exception:
        return None


def events(d):
    """-> [(kind, text)]；kind: T 正文 / N 名札 / O 选项 / B 枠开始 / L 软换行 / C 接续 / M 姓名宏"""
    ev, i, n = [], 0, len(d)
    while i < n - 5:
        if d[i] in (0x68, 0x64) and d[i + 1:i + 4] == b'\x00\x00\xff':
            L = d[i + 4]
            seg = d[i + 5:i + 5 + L]
            if L and all(0x21 <= b <= 0x7e for b in seg):
                s = jp(seg)
                if s:
                    ev.append(('T' if d[i] == 0x68 else 'N', s))
                    i += 5 + L
                    continue
        if d[i:i + 4] == b'\xf6\x01\x00\xff' and i + 6 < n:
            L = d[i + 6]
            seg = d[i + 7:i + 7 + L]
            if L and all(0x21 <= b <= 0x7e for b in seg):
                s = jp(seg)
                if s:
                    ev.append(('O', s))
                    i += 7 + L
                    continue
        op = d[i:i + 4]
        if op in BREAK:
            ev.append(('B', ''))
        elif op == b'\x69\x00\x00\xff':
            ev.append(('L', ''))
        elif op == b'\x6c\x00\x00\xff':
            ev.append(('C', ''))
        elif op == b'\x6a\x00\x00\xff':
            ev.append(('M', SURNAME))
        elif op == b'\x6b\x00\x00\xff':
            ev.append(('M', NAME))
        else:
            i += 1
            continue
        i += 4
    return ev


def boxes(ev):
    """-> [(kind, text)]；kind: T 正文行 / O 选项行"""
    out, cur, last = [], '', 'B'

    def flush():
        nonlocal cur
        if cur:
            out.append(('T', cur))
        cur = ''

    for kind, s in ev:
        if kind == 'T':
            if last in ('L', 'C', 'M'):
                cur += s
            else:
                flush()
                cur = s
            last = 'T'
        elif kind == 'M':
            cur += s
            last = 'M'
        elif kind == 'O':
            flush()
            out.append(('O', s))
            last = 'O'
        elif kind == 'N':
            last = 'N'
        elif kind == 'B':
            flush()
            last = 'B'
        else:                              # L / C
            last = kind
    flush()
    return out


def load(path):
    return boxes(events(open(path, 'rb').read()))


def natkey(p):
    m = re.search(r'S(\d+)\.VML$', os.path.basename(p))
    return int(m.group(1)) if m else 9999


def tidy(t):
    """信件页的对齐填充（连续全角空格）属版式，收敛为单个间隔。"""
    t = re.sub(SPACE + '{2,}', SPACE, t)
    return t.strip(SPACE)


if __name__ == '__main__':
    root = sys.argv[1]
    t = o = 0
    for f in sorted(glob.glob(os.path.join(root, '*.VML')), key=natkey):
        for k, s in load(f):
            t += (k == 'T')
            o += (k == 'O')
    print('正文行', t, '选项行', o)
