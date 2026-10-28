#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""水の旋律 ～協奏曲～ (PC) 剧本成行 —— mlk/ADV 脚本 (cp932)
命令: mes(名, 文[, 声]) / p() 改页点击 / l() 框内点击(不改页) / select(文,标签,...)
成行: 一行 = 一次点击 = 一个 mes；同框(l 连接)多段先逐段再合并(ABC)。
名札: 独立名字窗 ⇒ 丢名（不加前缀）。
"""
import glob, os, re, sys

SRC = r'_src_mizumelody/arc/script'
OUT = r'提取结果/[PC-JP]水の旋律 ～協奏曲～.txt'


def strip_comments(t):
    out = []
    i, n = 0, len(t)
    instr = False
    while i < n:
        c = t[i]
        if instr:
            out.append(c)
            if c == '\\' and i + 1 < n:
                out.append(t[i + 1]); i += 2; continue
            if c == '"':
                instr = False
            i += 1; continue
        if c == '"':
            instr = True; out.append(c); i += 1; continue
        if t.startswith('//', i):
            j = t.find('\n', i)
            i = n if j < 0 else j
            continue
        if t.startswith('/*', i):
            j = t.find('*/', i + 2)
            i = n if j < 0 else j + 2
            continue
        out.append(c); i += 1
    return ''.join(out)


def parse_calls(t):
    """返回 [(name, [raw_args])]，按出现顺序。"""
    res = []
    for m in re.finditer(r'(?<![A-Za-z0-9_])([A-Za-z_][A-Za-z0-9_]*)\s*\(', t):
        name = m.group(1)
        i = m.end(); depth = 1; start = i; args = []
        instr = False
        while i < len(t) and depth:
            c = t[i]
            if instr:
                if c == '\\':
                    i += 2; continue
                if c == '"':
                    instr = False
            elif c == '"':
                instr = True
            elif c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    args.append(t[start:i]); break
            elif c == ',' and depth == 1:
                args.append(t[start:i]); start = i + 1
            i += 1
        res.append((name, [a.strip() for a in args]))
    return res


def unq(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        body = s[1:-1]
        body = body.replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\')
        return body
    return None


def flat(s):
    """段内软换行合并：去掉换行"""
    return s.replace('\r', '').replace('\n', '')


def main():
    files = sorted(glob.glob(os.path.join(SRC, 'ms*.cpp')),
                   key=lambda p: int(re.search(r'ms(\d+)', os.path.basename(p)).group(1)))
    lines = []
    st = dict(box=0, seg=0, opt=0, single=0)
    for f in files:
        t = strip_comments(open(f, 'rb').read().decode('cp932'))
        segs = []          # 当前框内的段
        for name, args in parse_calls(t):
            if name == 'mes':
                txt = None; nm = None
                if len(args) >= 2:
                    nm = unq(args[0]); txt = unq(args[1])
                elif len(args) == 1:
                    txt = unq(args[0])
                if txt is None:
                    continue
                segs.append(flat(txt))
            elif name == 'l':
                st['seg'] += 1
                # 段结束，继续同框
            elif name == 'p':
                if segs:
                    if len(segs) == 1:
                        lines.append(segs[0]); st['single'] += 1
                    else:
                        lines.extend(segs)
                        lines.append(''.join(segs))
                        st['box'] += 1
                    st['seg'] += 0
                segs = []
            elif name == 'select':
                if segs:
                    if len(segs) == 1:
                        lines.append(segs[0]); st['single'] += 1
                    else:
                        lines.extend(segs); lines.append(''.join(segs)); st['box'] += 1
                    segs = []
                texts = [unq(a) for a in args]
                # 形如 ("文","标签","文","标签",...)
                for k in range(0, len(texts) - 1, 2):
                    if texts[k] is not None and texts[k + 1] is not None:
                        lines.append(flat(texts[k])); st['opt'] += 1
        if segs:
            if len(segs) == 1:
                lines.append(segs[0]); st['single'] += 1
            else:
                lines.extend(segs); lines.append(''.join(segs)); st['box'] += 1
    lines = [l for l in lines if l.strip()]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('scripts', len(files), 'lines', len(lines), st)


if __name__ == '__main__':
    main()
