#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RPG Maker XP/VX Scripts.rxdata 解压到 .rb（zlib 逐本解压）。

用法: python rxdata_scripts_dump.py <Scripts.rxdata> <out_dir>
依赖: rubymarshal
"""
import sys, os, zlib
from rubymarshal.reader import load

def main():
    src, out = sys.argv[1], sys.argv[2]
    obj = load(open(src, 'rb'))
    os.makedirs(out, exist_ok=True)
    for row in obj:
        sid, name, code = row[0], row[1], row[2]
        nm = name.decode('utf-8', 'replace') if isinstance(name, bytes) else str(name)
        try:
            text = zlib.decompress(code).decode('utf-8', 'replace')
        except Exception as e:
            print('ERR', nm, e); continue
        open(os.path.join(out, '%05d_%s.rb' % (sid, nm)), 'w', encoding='utf-8').write(text)
    print('dumped', len(obj))

if __name__ == '__main__':
    main()
