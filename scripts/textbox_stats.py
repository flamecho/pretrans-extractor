#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统计用 —— 分作行数 + 文本框封口 op 分布（L0 判据的证据）。"""
import collections
import sys, os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glob
import os
import re
import sys

import lz4.block
import msgpack
import UnityPy

JP = re.compile('[\u3040-\u30ff\u4e00-\u9fff]')
TEXT_CMDS = (b'maintxt_print', b'maintxt_print_c')
TAG = re.compile(r'<[^<>]{1,48}>')
D = os.path.join(VNTRANS_HOME, "_w_p4_jusanshi/rf/Data/StreamingAssets/aa/Switch")


def bundle_text(path):
    env = UnityPy.load(path)
    for o in env.objects:
        if o.type.name == 'TextAsset':
            d = o.read()
            s = d.m_Script
            return (s.encode('utf-8', 'surrogateescape') if isinstance(s, str) else bytes(s))
    return None


def decompress_mp(raw):
    top = msgpack.unpackb(raw, raw=True, strict_map_key=False)
    bins = [x for x in top if isinstance(x, (bytes, bytearray))]
    exts = [x for x in top if isinstance(x, msgpack.ExtType)]
    if not exts:
        return b''.join(bytes(b) for b in bins)
    ext = exts[0].data
    lens = [int.from_bytes(ext[i + 1:i + 3], 'big') for i in range(0, len(ext) - 2, 3)]
    if len(lens) != len(bins):
        raw_join = b''.join(bytes(b) for b in bins)
        try:
            msgpack.unpackb(raw_join, raw=True, strict_map_key=False)
            return raw_join
        except Exception:
            return None
    return b''.join(lz4.block.decompress(bytes(c), uncompressed_size=lens[i]) for i, c in enumerate(bins))


def main():
    files = sorted(glob.glob(os.path.join(D, '*advscripts-jyuza*')))
    stat = collections.defaultdict(lambda: {'files': 0, 'lines': 0, 'chars': 0})
    bound = collections.Counter()     # 封口 op（文本框结束处紧邻的下一个 op）
    inner = collections.Counter()     # 同一框内被合并时夹在中间的 op（理论上是 0）
    softc = 0
    for p in files:
        g = 'jyuza1' if 'jyuza1-' in p else 'jyuza2'
        raw = bundle_text(p)
        import jusanshi as J
        body = J.decompress_mp(raw)
        stat[g]['files'] += 1
        if body is None:
            continue
        doc = msgpack.unpackb(body, raw=True, strict_map_key=False)
        # 线性化：DFS 文档序
        seq = []

        def walk(e):
            for x in e or []:
                seq.append(x)
                walk(x.get(b'Elements'))
        walk(doc.get(b'Functions'))

        # 统计封口 op：text 段之后的第一个非 text op
        prev_text = False
        for x in seq:
            is_text = x.get(b'Name') in TEXT_CMDS
            if prev_text and not is_text:
                bound[x.get(b'Name')] += 1
            prev_text = is_text

        # 出框：**直接复用成品提取器**，保证与交付文件逐行一致
        out = []
        J.walk(doc.get(b'Functions'), out)

        stat[g]['lines'] += len(out)
        stat[g]['chars'] += sum(len(x) for x in out)

    for g in sorted(stat):
        s = stat[g]
        print('%s: bundles %d, lines %d, chars %d' % (g, s['files'], s['lines'], s['chars']))
    print('total lines', sum(s['lines'] for s in stat.values()))
    print('soft-carry(引号未闭合而继续吸收) 次数', softc)
    print('--- 封口 op Top20（紧跟在 maintxt_print 段之后的第一个 op）')
    for k, v in bound.most_common(20):
        print('  %-20s %d' % (k.decode('utf8', 'replace') if k else k, v))


if __name__ == '__main__':
    main()
