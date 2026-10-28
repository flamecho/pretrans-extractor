#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""薄桜鬼 遊戯録 隊士達の大宴会 (NS) —— STCM2L 提取器 v2。

L0 判据
  指令 = [u32 op][u32 nparams][u32 len] + nparams*12B + (可选)内联串记录
  串记录 = [u32 a][u32 L/4][u32 1][u32 L][utf8][NUL pad]；op 的 p0 = 该记录的绝对偏移
  op 0x4BA = 正文段  0x4BC = 名札（独立名窗，丢弃）
     0x4C0 = 扉文/章题（上屏）  0x4CF = 选项  0x4CE = 选项组结束
     0x4BB = 点击等待；0x41B/0x41C/0x41D = 按名访问变量（引擎在这些点冲刷文本框；
       只取 0x4BB 作断点会出现 >3 行同框、跨名札粘行）
断点击 ⇒ 一次点击 = 两条 {0x4BB,0x41B,0x41C,0x41D} 之间
同一点击内的 0x6(goto) 互斥分支 ⇒ 取不含 #Name[ 的版本（直写名版），全含则取最长

用法: python hakuoki_ns_extract2.py [out.txt]
"""
import sys, os, glob, struct, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, '_work_hakuoki_ns', 'cpk')

A4 = lambda n: (n + 3) & ~3
WAIT = {0x4BB, 0x41B, 0x41C, 0x41D}
TEXT, NAME, OPT, TITLE, GOTO = 0x4BA, 0x4BC, 0x4CF, 0x4C0, 0x6
HERO = '千鶴'
# 本作只有 6 种宏形态：#Name[0/1] #Scale[..] #Speed[..]（全库统计，无裸 #n）
MACRO = re.compile(r'#[A-Za-z]+\[[^\]]*\]')
NAME_MACRO = re.compile(r'#Name\[\d+\]')


def strings(body):
    out, o, n = [], 0, len(body)
    while o + 16 <= n:
        a, l4, one, L = struct.unpack_from('<4I', body, o)
        if one != 1 or L % 4 or L < 4 or o + 16 + L > n:
            break
        raw = body[o + 16:o + 16 + L].rstrip(b'\x00')
        try:
            s = raw.decode('utf-8')
        except Exception:
            break
        if A4(len(raw) + 1) != L:
            break
        out.append(s)
        o += 16 + L
    return out


def walk(path):
    d = open(path, 'rb').read()
    i = d.find(b'CODE_START_')
    if i < 0:
        return []
    o, n, recs = i + 16, len(d), []
    while o + 12 <= n:
        op, np_, ln = struct.unpack_from('<3I', d, o)
        if ln < 12 or ln % 4 or o + ln > n:
            break
        recs.append((op, strings(d[o + 12 + np_ * 12:o + ln])))
        o += ln
    return recs


def clean(s):
    return MACRO.sub('', NAME_MACRO.sub(HERO, s))


def seg_text(parts):
    """同框软换行合并：续行行首全角空格＝折行缩进 ⇒ 去掉后直接拼接。"""
    return ''.join(s.lstrip('\u3000') if k else s for k, s in enumerate(parts))


def extract(path):
    recs = walk(path)
    clicks, cur = [], []
    for gi, (op, ss) in enumerate(recs):
        if op in WAIT:
            clicks.append(cur)
            cur = []
        else:
            cur.append((gi, op, ss))
    if cur:
        clicks.append(cur)

    rows = []
    for ck in clicks:
        # 按 goto 切段（互斥分支）
        segs, s0 = [], 0
        for i, (gi, op, ss) in enumerate(ck):
            if op == GOTO:
                segs.append((s0, i))
                s0 = i + 1
        segs.append((s0, len(ck)))

        best, best_key = None, None
        for a, b in segs:
            txts = [ss[0] for gi, op, ss in ck[a:b] if op == TEXT and ss and ss[0].strip()]
            if not txts:
                continue
            body = seg_text(txts)
            key = (0 if '#Name[' in body else 1, len(body))
            if best_key is None or key > best_key:
                best, best_key = (a, b), key

        a, b = best if best else (0, 0)
        buf = []
        n_ck = len(ck)

        def flush():
            if buf:
                t = clean(seg_text(buf)).strip()
                if t:
                    rows.append(t)
                buf.clear()

        for i, (gi, op, ss) in enumerate(ck):
            if op == TEXT:
                if a <= i < b and ss and ss[0].strip():
                    buf.append(ss[0])
            elif op == TITLE and ss and ss[0].strip():
                # 章名表（0x3 索引取值）不是扉文：紧随 0x3 的 0x4C0 一律剔除
                if (gi + 1 < len(recs) and recs[gi + 1][0] == 0x3) or \
                   (gi > 0 and recs[gi - 1][0] == 0x3):
                    continue
                flush()
                rows.append('【%s】' % clean(ss[0]).strip())
            elif op == OPT and ss and ss[0].strip():
                flush()
                rows.append(clean(ss[0]).strip())
        flush()
    return rows


def main():
    dst = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, '_work_hakuoki_ns', 'out2.txt')
    tot = 0
    with open(dst, 'w', encoding='utf-8', newline='\n') as fh:
        for part in ('d00', 'd01', 'd02'):
            d = os.path.join(SRC, part, 'script')
            for f in sorted(glob.glob(os.path.join(d, '*')), key=lambda p: int(os.path.basename(p))):
                rows = extract(f)
                n = 0
                for t in rows:
                    t = t.strip()
                    if not t:
                        continue
                    fh.write(t + '\n')
                    n += 1
                tot += n
                print('%-12s %5d' % (part + '/' + os.path.basename(f), n))
    print('total', tot)


if __name__ == '__main__':
    main()
