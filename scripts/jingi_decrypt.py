# -*- coding: utf-8 -*-
"""仁義なき乙女 (CRPT type 3) 解密 —— 复用 tsundere 的 LCG 表/散列/scatter 核心，逐块 seed 复原。"""
import sys, os, re
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
import numpy as np
from tsundere_extract import decrypt_block, score_block

SRC = os.path.join(VNTRANS_HOME, '_work_jingi_honpen/src/仁義なき乙女/仁義なき乙女.sce')
OUT = os.path.join(VNTRANS_HOME, '_work_jingi_honpen/dec')
if len(sys.argv) > 1:
    SRC = sys.argv[1]
if len(sys.argv) > 2:
    OUT = sys.argv[2]


def main():
    data = open(SRC, 'rb').read()
    assert data[:4] == b'CRPT'
    pay = data[0x20:]
    NB = len(pay) // 0x400
    blocks = np.frombuffer(pay[:NB * 0x400], dtype=np.uint8).reshape(NB, 0x400)
    dec = []
    scores = []
    for bi in range(NB):
        base = decrypt_block(bytes(blocks[bi]))
        k, sc = score_block(np.frombuffer(base, dtype=np.uint8))
        dec.append(bytes(c ^ k for c in base))
        scores.append(sc)
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, 'full.bin'), 'wb').write(b''.join(dec))
    # 文本块（score>=150）
    txt = b'\x00'.join(d for d, s in zip(dec, scores) if s >= 150)
    open(os.path.join(OUT, 'textblocks.bin'), 'wb').write(txt)
    hi = sum(1 for s in scores if s >= 150)
    print('NB=%d text_blocks=%d head=%s' % (NB, hi, b''.join(dec)[:32].hex(' ')))
    print('score distribution min/max=%d/%d' % (min(scores), max(scores)))


if __name__ == '__main__':
    main()
