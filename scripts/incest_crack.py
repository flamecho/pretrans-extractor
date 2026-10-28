#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""周期 keystream 破解：c[i] = p[i] ^ key[i % P]，key 每文件独立。
用 cp932 文本二元模型 + ICM 逐相位最大似然迭代（每相位 ≤256 候选，非穷举密钥空间）。
用法: python scripts/incest_crack.py <entry-name> [P]
"""
import zlib, numpy as np, math, collections, sys, os
exec(open(os.path.join(os.path.dirname(__file__), 'incest_filter.py')).read().split('def main')[0])

MODEL = '_work_incest/_sjis_model.npz'


def build_model():
    if os.path.exists(MODEL):
        z = np.load(MODEL)
        return z['uni'], z['bi']
    txt = open('提取结果/[PC-JP]END END SUMMER.txt', 'rb').read().decode('utf-8', 'ignore')
    b = txt.encode('cp932', 'ignore')
    uni = np.zeros(256)
    bi = np.zeros((256, 256))
    for i, v in enumerate(b):
        uni[v] += 1
        if i:
            bi[b[i - 1], v] += 1
    uni = np.log((uni + 0.5) / (len(b) + 128))
    bi = np.log((bi + 0.05) / (bi.sum(axis=1, keepdims=True) + 12.8))
    np.savez(MODEL, uni=uni, bi=bi)
    return uni, bi


def crack(name, P=1891, sweeps=5):
    uni, bi = build_model()
    d, items = load_idx()
    C = {x[0]: x for x in items}
    it = C[name]
    sf, o, osz, cs = it[2][0]
    c = np.frombuffer(zlib.decompress(d[o:o + cs]) if sf & 0xff else d[o:o + cs], dtype=np.uint8).copy()
    N = len(c)
    key = np.zeros(P, dtype=np.uint8)
    # 第一遍：单字节模型
    for j in range(P):
        idx = np.arange(j, N, P)
        cand = c[idx][None, :] ^ np.arange(256, dtype=np.uint8)[:, None]
        s = uni[cand].sum(axis=1)
        key[j] = int(np.argmax(s))
    p = c ^ np.resize(key, N)
    for itn in range(sweeps):
        order = range(P) if itn % 2 == 0 else range(P - 1, -1, -1)
        for j in order:
            idx = np.arange(j, N, P)
            prev = p[np.maximum(idx - 1, 0)]
            nxt = p[np.minimum(idx + 1, N - 1)]
            cand = c[idx][None, :] ^ np.arange(256, dtype=np.uint8)[:, None]
            s = bi[prev[None, :], cand].sum(axis=1) + bi[cand, nxt[None, :]].sum(axis=1)
            kb = int(np.argmax(s))
            key[j] = kb
            p[idx] = c[idx] ^ kb
        ok = (zlib.adler32(p.tobytes()) & 0xffffffff) == it[3]
        print('  sweep %d adler_ok=%s' % (itn, ok))
        if ok:
            break
    out = p.tobytes()
    print('target=%08x got=%08x' % (it[3], zlib.adler32(out) & 0xffffffff))
    print('head:', repr(out[:160]))
    return out, key


if __name__ == '__main__':
    nm = sys.argv[1]
    P = int(sys.argv[2]) if len(sys.argv) > 2 else 1891
    out, key = crack(nm, P)
    fn = '_work_incest/crack_' + nm.replace('/', '_')
    open(fn, 'wb').write(out)
    print('->', fn)
