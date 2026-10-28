# -*- coding: utf-8 -*-
"""合成最终交付文本（一次点击 = 一行）。"""
import glob, os, sys, struct

NAME1 = '国東'
NAME2 = '綴'


def blocks(d):
    i = 0
    n = len(d)
    res = []
    while True:
        j = d.find(b'\xaa\x00', i)
        if j < 0 or j + 6 > n:
            break
        k = d.find(b'\x00\x00', j + 4)
        if k < 0:
            break
        txt = d[j + 4:k]
        ok = False
        if txt and all(0x20 <= b < 0x100 for b in txt):
            after = k + 2
            while after < k + 6 and d[after] == 0:
                after += 1
            if d[after:after + 4] == b'\xab\x00\x00\x00':
                ok = True
        if ok:
            res.append((struct.unpack('<H', d[j + 2:j + 4])[0], txt))
            i = k + 2
        else:
            i = j + 1
    return res


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else '_work_thc/files3'
    out = sys.argv[2] if len(sys.argv) > 2 else '提取结果/x.txt'
    lines = []
    ids = []
    for fn in sorted(glob.glob(os.path.join(src, '*.bin'))):
        d = open(fn, 'rb').read()
        for mid, raw in blocks(d):
            s = raw.decode('cp932')
            s = s.replace('||', '')
            s = s.replace('\\1', NAME1).replace('\\2', NAME2)
            s = s.replace('\u3000\u3000', '\u3000')
            s = s.strip()
            if not s:
                continue
            lines.append(s)
            ids.append(mid)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(lines) + '\n')
    print('lines', len(lines), 'ids', min(ids), max(ids))
    miss = [x for x in range(min(ids), max(ids) + 1) if x not in set(ids)]
    print('missing ids', len(miss), miss[:10])


if __name__ == '__main__':
    main()
