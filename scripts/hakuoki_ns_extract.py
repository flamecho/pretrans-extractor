#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""薄桜鬼 遊戯録 隊士達の大宴会 (NS) —— STCM2L 文本提取器（v1，逐文件调试输出）。
> **两版并存**：`hakuoki_ns_extract2.py` 是定稿（按 L0 判据成行）；本版是调试版，
> 但**带完整的指令结构 / 串记录形状 / op 表**（`0x4BA=TEXT` 等），当引擎参考读这版。

引擎：Idea Factory STCM2L（NS 变体，字符串 UTF-8）
  指令 = [u32 op][u32 nparams][u32 length] + nparams*12B + 内联串区
  串记录 = [u32 a][u32 L/4][u32 1][u32 L][utf8][NUL pad]
  op: 0x4BA=TEXT 0x4BC=NAME 0x4BB=WAIT 0x4CF=OPT 0x4C0=TITLE
      0x41B/0x41C/0x41D=按名访问变量（亦断点击）

行粒度（L0）：一次点击 = 两条 WAIT 之间；同框内多条 0x4BA 为软换行 ⇒ 合并。
  一次点击内出现第二个 0x4BC（同名）＝ A/B 互斥变体（字面名版 / #Name 宏版）⇒ 只取首段。

用法: python hakuoki_ns_extract.py <script 目录> <out.txt>
"""
import sys, os, glob, struct, re

A4 = lambda n: (n + 3) & ~3
WAIT = {0x4BB, 0x41B, 0x41C, 0x41D}
TEXT, NAME, OPT, TITLE = 0x4BA, 0x4BC, 0x4CF, 0x4C0
MACRO = re.compile(r'#[A-Za-z][A-Za-z0-9_]*(?:\[[^\]]*\])?')
NAME_MACRO = re.compile(r'#Name\[1\]')
HERO = '千鶴'


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


def walk(d):
    i = d.find(b'CODE_START_')
    if i < 0:
        return []
    o, n, recs = i + 16, len(d), []
    while o + 12 <= n:
        op, np_, ln = struct.unpack_from('<3I', d, o)
        if ln < 12 or ln % 4 or o + ln > n:
            break
        wait = op in WAIT
        recs.append((op, strings(d[o + 12 + np_ * 12:o + ln])))
        o += ln
    return recs


def clean(s):
    s = NAME_MACRO.sub(HERO, s)
    s = MACRO.sub('', s)
    return s.replace('\u3000', ' ').strip() if False else s.strip()


def extract(path):
    """返回 [(kind, text, name)]，kind ∈ {'line','opt','title'}。"""
    recs = walk(open(path, 'rb').read())
    out = []
    segs = []          # 当前点击的分段: [[name, [text...]]]
    cur = None

    def flush():
        nonlocal segs, cur
        if segs:
            # A/B 变体：同一点击内多个分段（各带名札）⇒ 取首段
            _name, parts = segs[0]
            t = ''.join(parts)
            if t.strip():
                out.append(('line', t, _name))
        segs, cur = [], None

    for op, ss in recs:
        if op in WAIT:
            flush()
        elif op == NAME:
            cur = [ss[0] if ss else '', []]
            segs.append(cur)
        elif op == TEXT:
            if cur is None:
                cur = ['', []]
                segs.append(cur)
            if ss:
                cur[1].append(ss[0])
        elif op in (0x4C0, OPT):
            flush()
            if ss and ss[0].strip():
                out.append(('title' if op == TITLE else 'opt', ss[0], ''))
    flush()
    return out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    files = (sorted(glob.glob(os.path.join(src, '*'))) if os.path.isdir(src) else [src])
    tot = 0
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as fh:
        for f in files:
            if not os.path.isfile(f):
                continue
            rows = extract(f)
            n = 0
            for kind, t, name in rows:
                t = clean(t)
                if not t:
                    continue
                if kind == 'title':
                    t = '【%s】' % t
                fh.write(t + '\n')
                n += 1
            tot += n
            print('%-30s %4d' % (os.path.basename(f), n))
    print('total', tot)


if __name__ == '__main__':
    main()
