#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《逢魔が刻 ～かくりよの縁～》(PSVita / PCSG00769) 游戏内文本提取

引擎 (逆向结论):
  · 容器    NSAC v2 —— 见 scripts/nsac.py
  · 贴图/字体 "nismultitexform" (NIS Multi Texture) —— .nmt / .nmf
  · 文本表  DB 格式: {u32 count, u32 field1, u32 dataOffset, u32 headerSize}
            字符串区 dataOffset 起, 0x00 分隔的 UTF-8

用法:  python ouma_extract.py <dec/database.dat> <outdir>
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nsac import Nsac  # noqa

JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff\uff00-\uffef\u3000-\u303f]')


def split_strings(blob):
    """0x00 分隔的 UTF-8 字符串 (保持出现顺序, 去重)"""
    out = []
    seen = set()
    pos = 0
    L = len(blob)
    while pos < L:
        e = blob.find(b'\x00', pos)
        if e < 0:
            e = L
        s = blob[pos:e]
        if s:
            t = s.decode('utf-8', 'replace')
            if t not in seen:
                seen.add(t)
                out.append(t)
        pos = e + 1
    return out


def main():
    if len(sys.argv) < 3:
        sys.stderr.write(__doc__)
        sys.exit(2)
    dbpath, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    arc = Nsac(open(dbpath, 'rb').read())
    print('NSAC entries:', len(arc.named))

    summary = []
    for name, off, size in arc.named:
        blob = arc.b[off:off + size]
        alls = split_strings(blob)
        jp = [s for s in alls if JP.search(s)]
        summary.append((name, size, len(alls), len(jp)))
        safe = name.replace('/', '_').replace('\\', '_')
        with open(os.path.join(outdir, safe + '.txt'), 'w',
                  encoding='utf-8-sig', newline='\n') as f:
            for s in alls:
                f.write(s.replace('\n', ' ').replace('\r', '') + '\n')

    print('%-26s %10s %9s %9s' % ('file', 'size', 'strings', 'japanese'))
    for name, size, n, jp in summary:
        print('%-26s %10d %9d %9d' % (name, size, n, jp))


if __name__ == '__main__':
    main()
