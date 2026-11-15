# -*- coding: utf-8 -*-
"""LoverPretend STCM2L 节点扫描（L = align4(len+1)，含 NUL+padding）"""
import struct, collections, os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

U = lambda d, o: struct.unpack_from('<I', d, o)[0]

def scan(d):
    out = []
    n = len(d)
    for t in range(0, n - 20):
        if d[t:t+4] != b'\x00\x00\x00\x00':
            continue
        L = U(d, t + 12)
        if L < 4 or L > 16384 or L & 3:
            continue
        if U(d, t + 4) != L // 4 or U(d, t + 8) != 1:
            continue
        raw = d[t + 16:t + 16 + L].rstrip(b'\x00')
        if not raw:
            continue
        try:
            s = raw.decode('utf-8')
        except UnicodeDecodeError:
            continue
        if any(ord(c) < 0x20 for c in s):
            continue
        if (len(raw) + 1 + 3) // 4 * 4 != L:
            continue
        out.append((t, L, U(d, t - 16), s))
    return out

if __name__ == '__main__':
    SD = os.path.join(VNTRANS_HOME, '_w_lpv/story/SCRIPT')
    tot = collections.Counter(); ch = collections.Counter()
    files = 0; nodes = 0
    for f in sorted(os.listdir(SD)):
        if not f.endswith('.DAT'): continue
        files += 1
        for t, L, K, s in scan(open(os.path.join(SD, f), 'rb').read()):
            tot[K] += 1; ch[K] += len(s); nodes += 1
    print('files', files, 'nodes', nodes, 'chars', sum(ch.values()))
    for k, v in tot.most_common(20):
        print('  KIND %-12s n=%6d chars=%7d avg %.1f' % (hex(k), v, ch[k], ch[k]/v))
