# -*- coding: utf-8 -*-
"""用 cx_vm2 的真算法批量解密 scenario/*.txt → out2/，并做坏字节统计。

hash 来源：data.xp3 的 XP3 索引（zlib 压缩，偏移 0x1bcd8189）里每个条目的
adlr 字段 —— 即 adler32(明文)，引擎正是拿它当 CX 的 hash。
"""
import glob
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cx_vm2 as C

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, '..', '_src_ginkoku', 'data', 'scenario')
OUT = os.path.join(ROOT, 'out2')
INDEX = os.path.join(ROOT, 'xp3_index.bin')


def load_hashes():
    idx = open(INDEX, 'rb').read()
    p = 0
    ent = {}
    while p + 12 <= len(idx) and idx[p:p + 4] == b'File':
        size = struct.unpack_from('<Q', idx, p + 4)[0]
        body = idx[p + 12:p + 12 + size]
        cs = struct.unpack_from('<Q', body, 4)[0]
        data = body[12:12 + cs]
        nlen = struct.unpack_from('<H', data, 20)[0]
        name = data[22:22 + nlen * 2].decode('utf-16-le')
        adlr = None
        q = 12 + cs
        while q + 12 <= len(body):
            cn = body[q:q + 4]
            c2 = struct.unpack_from('<Q', body, q + 4)[0]
            if cn == b'adlr':
                adlr = struct.unpack_from('<I', body, q + 12)[0]
            q += 12 + c2
        ent[name] = adlr
        p += 12 + size
    return ent


def audit(t):
    try:
        s = t.decode('cp932')
    except UnicodeDecodeError as e:
        return dict(fail=str(e), ufffd=99, hankaku=99, pua=99, ctrl=99)
    return dict(fail=None,
                ufffd=s.count('\ufffd'),
                hankaku=sum(1 for ch in s if 0xff61 <= ord(ch) <= 0xff9f),
                pua=sum(1 for ch in s if 0xe000 <= ord(ch) <= 0xf8ff),
                ctrl=sum(1 for ch in s if ord(ch) < 0x20 and ch not in '\r\n\t'))


def main():
    ent = load_hashes()
    files = sorted(glob.glob(os.path.join(SRC, '*.txt')))
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for f in files:
        name = os.path.basename(f)
        h = ent.get('scenario/' + name)
        if h is None:
            print('NO HASH', name)
            continue
        d = bytearray(open(f, 'rb').read())
        bnd, k1, k2 = C.decode(d, h)
        open(os.path.join(OUT, name), 'wb').write(d)
        a = audit(bytes(d))
        rows.append(dict(name=name, n=len(d), hash=h, idx=h & 0x7f, bnd=bnd,
                         k1='%02X' % k1['k0'], k2=('%02X' % k2['k0']) if k2 else None,
                         start=k1['start'], end=k1['end'],
                         start2=k2['start'] if k2 else None,
                         end2=k2['end'] if k2 else None, **a))
    tot = len(rows)
    badn = sum(1 for r in rows if r['fail'] or r['ufffd'] or r['hankaku'] or r['pua'] or r['ctrl'])
    print('files=%d  坏文件=%d  UFFFD=%d 半角假名=%d 私用区=%d 控制字节=%d' % (
        tot, badn, sum(r['ufffd'] for r in rows), sum(r['hankaku'] for r in rows),
        sum(r['pua'] for r in rows), sum(r['ctrl'] for r in rows)))
    for r in rows:
        if r['fail'] or r['ufffd'] or r['hankaku'] or r['pua'] or r['ctrl']:
            print('  BAD', r['name'], r['fail'], r['ufffd'], r['hankaku'], r['pua'], r['ctrl'])
    json.dump(rows, open(os.path.join(ROOT, '_decrypt_report2.json'), 'w'), ensure_ascii=False)
    return rows


if __name__ == '__main__':
    main()
