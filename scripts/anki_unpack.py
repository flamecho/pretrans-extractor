# -*- coding: utf-8 -*-
"""アンジェリーク 魔恋の六騎士 (PSP/ULJM05986) UNION.CPK 解包
- 条目名＝纯数字 ID（对应 EBOOT 内 %s/%05d：system/sub/script/back/chara/etc/sound）
- CRILAYLA 解压 -> STCM2L 脚本落到 _work_anki/script/<id>.bin，其余按类型统计
用法: python scripts/anki_unpack.py <lo> <hi>
"""
import sys, os, struct, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
import cpk

SRC = os.path.join(VNTRANS_HOME, '待核实/_trans/_work_anki/UNION.CPK')
OUT = os.path.join(VNTRANS_HOME, '待核实/_trans/_work_anki/script')
os.makedirs(OUT, exist_ok=True)

c = cpk.CPK(SRC)
lo, hi = int(sys.argv[1]), int(sys.argv[2])
cnt = collections.Counter()
sc = []
for e in c.entries[lo:hi]:
    try:
        c.f.seek(e['offset']); b = c.f.read(e['FileSize'])
        if b[:8] == b'CRILAYLA':
            us = struct.unpack_from('<I', b, 8)[0]
            if us <= 0 or us > 20_000_000:
                cnt['BADHDR'] += 1
                continue
            d = cpk.crilayla_decompress(b)
        else:
            d = b
        if d[:6] == b'STCM2L':
            open(os.path.join(OUT, '%05d.bin' % e['id']), 'wb').write(d)
            sc.append((e['id'], len(d)))
            cnt['STCM2L'] += 1
        elif d[:4] in (b'GIM2', b'ART2'):
            cnt['IMG'] += 1
        elif d[:4] == b'CPK ':
            cnt['CPK'] += 1
            open(os.path.join(OUT, 'nested_%05d.cpk' % e['id']), 'wb').write(d)
        else:
            cnt['o:' + d[:4].hex()] += 1
        del d, b
    except Exception:
        cnt['ERR'] += 1
print('[%d:%d]' % (lo, hi), cnt.most_common(8))
print('STCM2L ids:', [i for i, _ in sc][:20], '...' if len(sc) > 20 else '')
