#!/usr/bin/env python3
"""tennis_dump.py -- 解出全部 .s 的消息原文（含 gaiji 原字节），落 TSV 供分析.

输出: _work_tennis/msgs.tsv   每行: file <TAB> idx <TAB> hex_escaped_text
      hex_escaped: 把 0x84xx/其他非 cp932 可解码写成 \\x84\\x82，其余原样（cp932 -> utf8）
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tennis_scan import load_scriptbin, get_scpt, WORK

OUT = os.path.join(WORK, 'msgs.tsv')


def dec_seg(s):
    """按 cp932 解，未定义字节写成 \\xNN。"""
    out = []
    i = 0
    while i < len(s):
        b = s[i]
        if b < 0x80:
            out.append(chr(b))
            i += 1
            continue
        if 0xa1 <= b <= 0xdf:
            try:
                out.append(s[i:i + 1].decode('cp932'))
            except Exception:
                out.append('\\x%02x' % b)
            i += 1
            continue
        try:
            out.append(s[i:i + 2].decode('cp932'))
            i += 2
        except Exception:
            out.append('\\x%02x' % b)
            i += 1
    return ''.join(out)


def main():
    names, offs, sizes, f = load_scriptbin()
    rows = []
    bad = []
    for i, nm in enumerate(names):
        if not nm.endswith('.s'):
            continue
        f.seek(offs[i])
        d = f.read(sizes[i])
        try:
            inner, sc = get_scpt(d)
        except Exception as e:
            bad.append((nm, repr(e)))
            continue
        if len(sc) < 0x20 or sc[:4] != b'SCPT':
            bad.append((nm, 'not SCPT'))
            continue
        h = struct.unpack_from('<8I', sc, 0)
        B = h[6]
        if B == 0 or B + 8 > len(sc):
            continue
        blen = struct.unpack_from('<I', sc, B + 4)[0]
        bs = B + blen + 1
        blob = sc[bs:]
        p = 0
        idx = 0
        while p < len(blob):
            e = blob.find(b'\x00', p)
            if e < 0:
                e = len(blob)
            seg = blob[p:e]
            if seg:
                rows.append((nm, inner, idx, dec_seg(seg)))
                idx += 1
            p = e + 1
    with open(OUT, 'w', encoding='utf-8', newline='\n') as o:
        for nm, inner, idx, t in rows:
            o.write('%s\t%s\t%d\t%s\n' % (nm, inner, idx, t.replace('\t', '\\t')))
    print('rows', len(rows), 'files_bad', len(bad))
    for b in bad[:10]:
        print('  bad', b)


if __name__ == '__main__':
    main()
