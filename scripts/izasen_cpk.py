#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""いざ、出陣！恋戦 data.cpk 解包（CPK 名 cp932 修正版）"""
import os
import sys
import struct

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cpk_v1
from cpk_v1 import CPK, TYPE_STRING, u32


class CPK932(CPK):
    def _cstr(self, buf, off, base):
        if off == 0:
            return ''
        p = base + off
        if p < 0 or p >= len(buf):
            return ''
        end = buf.find(b'\x00', p)
        if end < 0:
            end = len(buf)
        raw = bytes(buf[p:end])
        try:
            return raw.decode('cp932')
        except Exception:
            return raw.decode('cp932', 'replace')


if __name__ == '__main__':
    src = sys.argv[1]
    c = CPK932(src)
    print('Files=%s TocOffset=%s ContentOffset=%s' % (c.Files, c.TocOffset, c.ContentOffset))
    print('entries:', len(c.entries))
    exts = {}
    for e in c.entries:
        n = e['name'] or ''
        ext = os.path.splitext(n)[1].lower()
        exts[ext] = exts.get(ext, 0) + 1
    for k, v in sorted(exts.items(), key=lambda x: -x[1])[:25]:
        print('  ext %-8s %d' % (k or '(none)', v))
    if len(sys.argv) > 2:
        outdir = sys.argv[2]
        only = sys.argv[3] if len(sys.argv) > 3 else None
        n = 0
        for e in c.entries:
            name = e['name'] or ('%04d' % n)
            if only and not name.lower().endswith(only):
                continue
            name = name.replace('\\', '/').lstrip('/')
            name = ''.join(('_' if ch in '<>:"|?*' or ord(ch) < 32 else ch) for ch in name)
            name = '/'.join(p.rstrip(' .') or '_' for p in name.split('/'))
            dst = os.path.join(outdir, *name.split('/'))
            os.makedirs(os.path.dirname(dst) or outdir, exist_ok=True)
            with open(dst, 'wb') as o:
                o.write(c.raw(e))
            n += 1
        print('extracted:', n)
