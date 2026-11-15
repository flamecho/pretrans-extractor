# -*- coding: utf-8 -*-
"""探查 STCM2L 的 tag=0x35404 记录：8 槽 = 两套（各 4 槽：标记 + 3 行）"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import struct
import sys

ROOT = os.path.join(VNTRANS_HOME, '_w_lf/story/SCRIPT')
HERO = 'ヴィオレット'
TAG = 0x35404
PAT = struct.pack('<II', 1, TAG)      # pre=1, tag=0x35404

U = lambda d, o: struct.unpack_from('<I', d, o)[0]


def norm(s):
    return re.sub(r'[\s\u3000]', '', s.replace('#Name[1]', HERO))


def slots(d, i, n):
    out = []
    for k in range(n):
        p = U(d, i + 16 + 12 * k)
        s, raw = '', b''
        if p and p + 16 <= len(d) and U(d, p + 8) == 1:
            L = U(d, p + 12)
            raw = d[p + 16:p + 16 + L].rstrip(b'\x00')
            try:
                s = raw.decode('utf-8')
            except UnicodeDecodeError:
                s = ''
        out.append((p, raw, s))
    return out


def main(files):
    stats = {'rec': 0, 'eq': 0, 'prefix': 0, 'other': 0,
             'A_only': 0, 'B_only': 0, 'both_empty': 0}
    ex = {'other': [], 'prefix': [], 'A_only': [], 'B_only': []}
    marks = []
    for f in files:
        p = os.path.join(ROOT, f)
        try:
            d = open(p, 'rb').read()
        except OSError:
            continue
        if d[:6] != b'STCM2L':
            continue
        for m in re.finditer(re.escape(PAT), d):
            i = m.start()
            n, size = U(d, i + 8), U(d, i + 12)
            if n != 8 or size < 16 or i + size > len(d):
                continue
            sl = slots(d, i, n)
            A = norm(''.join(s for _, _, s in sl[1:4]))
            B = norm(''.join(s for _, _, s in sl[5:8]))
            stats['rec'] += 1
            marks.append((sl[0][1], sl[4][1]))
            if not A and not B:
                stats['both_empty'] += 1
            elif not A:
                stats['B_only'] += 1
                if len(ex['B_only']) < 6:
                    ex['B_only'].append((f, hex(i), B[:50]))
            elif not B:
                stats['A_only'] += 1
                if len(ex['A_only']) < 6:
                    ex['A_only'].append((f, hex(i), A[:50]))
            elif A == B:
                stats['eq'] += 1
            else:
                k = 0
                for x, y in zip(A, B):
                    if x != y:
                        break
                    k += 1
                if A.startswith(B) or B.startswith(A) or k / max(len(A), len(B)) > 0.5:
                    stats['prefix'] += 1
                    if len(ex['prefix']) < 6:
                        ex['prefix'].append((f, hex(i), A[:40], B[:40]))
                else:
                    stats['other'] += 1
                    if len(ex['other']) < 8:
                        ex['other'].append((f, hex(i), A[:40], B[:40]))
    print(stats)
    # 标记对：第二套标记 == 第一套 +1 ?
    from collections import Counter
    c = Counter()
    for a, b in marks:
        if len(a) == len(b) and a and b:
            ai, bi = int.from_bytes(a, 'little'), int.from_bytes(b, 'little')
            c['b=a+1' if bi == ai + 1 else 'other'] += 1
        else:
            c['len differ/empty'] += 1
    print('标记对关系', c.most_common())
    for k, v in ex.items():
        print('==', k)
        for row in v:
            print('   ', row)


if __name__ == '__main__':
    fs = sys.argv[1:] or sorted(f for f in os.listdir(ROOT) if f[0].isdigit() and f.endswith('.DAT'))
    main(fs)
