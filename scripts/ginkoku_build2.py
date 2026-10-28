# -*- coding: utf-8 -*-
"""成行（v2）：源 = _work_ginkoku/out2（按 tpm 真算法解出的台本）

规则沿用旧 assemble.py：
  块 = 一次点击（空行分隔）；块首名札行丢弃；块内软换行合并；
  选项按 [seladd text="..."] 顺序；`;` 注释行与 `*` 标签行丢弃。
本版新增（按交付格式）：
  `[○○○]`→綾、`[△△△]`→久世 之后，**其余 `[タグ]` 一律剔除**（含行内 SE/BGM 标签）。
输出：提取结果/[PC-JP]銀の冠碧の涙.txt（UTF-8 BOM + 纯 LF）
"""
import glob
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'out2')
OUT = os.path.join(ROOT, '..', '提取结果', '[PC-JP]銀の冠碧の涙.txt')

NAME_LINE = re.compile(r'^【[^】\[]{1,8}】$')
NAME_INLINE = re.compile(r'^[^「」\n]{0,12}】(?=「)')
TAG = re.compile(r'\[[^\[\]\r\n]{0,60}\]')


def sanitize(s):
    s = s.replace('[○○○]', '綾').replace('[△△△]', '久世')
    s = TAG.sub('', s)
    s = s.replace('\r', '').replace('\n', '')
    return s.strip()


def parse(path):
    t = open(path, 'rb').read().decode('cp932')
    res, blk = [], []

    def flush():
        nonlocal blk
        if not blk:
            return
        body = blk
        if NAME_LINE.match(body[0].strip()):
            body = body[1:]
        txt = sanitize(''.join(x.strip() for x in body))
        if txt:
            res.append(txt)
        blk = []

    for ln in t.split('\r\n'):
        s = ln.strip()
        if s == '':
            flush()
            continue
        if s.startswith(';') or s.startswith('*'):
            flush()
            continue
        if s.startswith('[') and s.endswith(']'):
            flush()
            m = re.match(r'^\[seladd\s+text="([^"]*)"', s)
            if m:
                res.append(sanitize(m.group(1)))
            continue
        blk.append(ln)
    flush()
    return res


def drop_cmd_lines(lines):
    return [l for l in lines if not (l.startswith('[') and '「' not in l)]


def strip_inline_name(txt):
    return '\n'.join(NAME_INLINE.sub('', l) for l in txt.split('\n'))


def main():
    files = sorted(glob.glob(os.path.join(SRC, '*.txt')))
    lines, per_file = [], []
    for p in files:
        got = parse(p)
        per_file.append((os.path.basename(p), len(got)))
        lines += got
    lines = drop_cmd_lines(lines)
    txt = '\n'.join(lines) + '\n'
    txt = strip_inline_name(txt)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write(txt)
    print('台本 %d 个  成行 %d 条  字符 %d' % (len(files), len(lines), len(txt)))
    print('输出:', OUT)
    zero = [n for n, c in per_file if c == 0]
    print('零产出台本:', len(zero), zero[:5])


if __name__ == '__main__':
    main()
