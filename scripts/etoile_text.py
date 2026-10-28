# -*- coding: utf-8 -*-
"""从解包出的 SCPT 里提取台词文本（一行 = 一个 message box）

SCPT 内文本块结构：
  [ASCII 标签]\x00\x00\x00\x00[SJIS 文本，\n 分行]\x00
标签（namesNNN / namehNNN / 场景跳转名）不进入正文。
"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import sys

LABEL = re.compile(rb'([\x20-\x7e]{2,})\x00\x00\x00\x00')
JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')


def extract(blob):
    """返回 [(label, text_lines)]，text_lines 已按 \n 拆开"""
    out = []
    for m in LABEL.finditer(blob):
        st = m.end()
        en = blob.find(b'\x00', st)
        if en < 0:
            continue
        raw = blob[st:en]
        if not raw or b'\x00' in raw:
            continue
        try:
            s = raw.decode('cp932')
        except UnicodeDecodeError:
            continue
        if not JP.search(s):
            continue
        lines = [x.strip() for x in s.split('\n')]
        lines = [x for x in lines if x]
        if lines:
            out.append((m.group(1).decode('ascii', 'replace'), lines))
    return out


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(VNTRANS_HOME, '_work_etoile/scpt')
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(VNTRANS_HOME, '_work_etoile/text.txt')
    files = sorted(f for f in os.listdir(src) if f.endswith('.scpt'))
    total = 0
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as fp:
        for f in files:
            blob = open(os.path.join(src, f), 'rb').read()
            rows = extract(blob)
            for _lab, lines in rows:
                fp.write(''.join(lines) + '\n')
                total += 1
    print('files=%d lines=%d -> %s' % (len(files), total, dst))


if __name__ == '__main__':
    main()
