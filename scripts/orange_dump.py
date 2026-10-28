#!/usr/bin/env python3
"""导出全部 .OHS 的字符串池为 TSV（file, idx, off, text）"""
import glob, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from orange_ohs import decrypt_text

out = sys.argv[1]
srcdir = sys.argv[2]
with open(out, 'w', encoding='utf-8', newline='\n') as w:
    for f in sorted(glob.glob(os.path.join(srcdir, '*.OHS'))):
        d = open(f, 'rb').read()
        blob, off = decrypt_text(d)
        for i, s in enumerate(blob.split(b'\x00')):
            t = s.decode('cp932', 'replace')
            t = t.replace('\t', ' ').replace('\r', '').replace('\n', '\\n')
            w.write('%s\t%d\t%d\t%s\n' % (os.path.basename(f), i, off, t))
print('done', out)
