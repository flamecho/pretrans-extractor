#!/usr/bin/env python3
"""金色のコルダ2f アンコール (PSP) - 递归解包 + 分类导出.

从 CDAR v4 容器里递归取出所有叶子文件，跳过图像/视频/大音频，
其余存到 outdir 供文本扫描。
"""
import sys, os, zlib, struct, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from corda2f_unpack import parse_cdar

IMG4 = (b'TIM2', b'PSMF', b'G1T\x00', b'MIG.', b'OMG\x00', b'SCR\x00')
IMG3 = (b'GIM',)


def main():
    src = sys.argv[1]
    base = int(sys.argv[2])
    outdir = sys.argv[3]
    os.makedirs(outdir, exist_ok=True)
    f = open(src, 'rb')
    f.seek(base)
    # 容器总大小 = 文件剩余（DATA.BIN 是 ISO 里最后一个大文件）
    d = f.read()
    print(f"container {len(d):,} bytes")
    leaves = parse_cdar(d, 0, '', None, [])
    print(f"leaves {len(leaves)}")
    cats = collections.Counter()
    manifest = []
    total = 0
    for path, off, dec, sz, data in leaves:
        m4 = data[:4]; m3 = data[:3]
        if m4 in IMG4 or m3 in IMG3 or (m4 == b'RIFF' and len(data) > 1 << 20):
            cats['skip-av'] += 1
            continue
        if m4 == b'RIFF' or m4 == b'\x89PNG':
            cats['audio/png'] += 1
        cats['kept'] += 1
        fn = path.replace('/', '_') + '.bin'
        with open(os.path.join(outdir, fn), 'wb') as g:
            g.write(data)
        total += len(data)
        manifest.append((path, len(data), m4.hex()))
    print(cats, 'kept bytes', total)
    with open(os.path.join(outdir, '_manifest.txt'), 'w', encoding='utf-8') as g:
        for path, n, m4 in manifest:
            g.write(f"{path}\t{n}\t{m4}\n")


if __name__ == '__main__':
    main()
