#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""三作解析自证数据（供报告引用）。"""
import collections
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dyc_extract import load_hdlg  # noqa: E402

TITLES = [
    ('liars', '_work_dydc/romfs_liars', '提取结果/[NS-JP]DYNAMIC CHORD feat.Liar-S Remaster edition.txt'),
    ('kyo', '_work_dydc/romfs_kyo', '提取结果/[NS-JP]DYNAMIC CHORD feat.KYOHSO Remaster Edition.txt'),
    ('apple', '_work_dydc/romfs_apple', '提取结果/[NS-JP]DYNAMIC CHORD feat.apple-polisher Remaster Edition.txt'),
]

out = {}
for tag, rom, txt in TITLES:
    sc = os.path.join(rom, 'Data/StreamingAssets/script')
    jp = os.path.join(sc, 'script_dialog_ja.hdlg')
    ja = load_hdlg(jp)
    en = load_hdlg(os.path.join(sc, 'script_dialog_en.hdlg'))
    d = {'hlg_count': len(ja), 'ja_bytes': os.path.getsize(jp),
         'en_bytes': os.path.getsize(os.path.join(sc, 'script_dialog_en.hdlg')),
         'heslnk_bytes': os.path.getsize(os.path.join(sc, 'script.heslnk'))}
    fam = {}
    for f in ('M', 'N', 'S', 'T', 'W'):
        idx = [i for i, k in enumerate(en) if k and re.match(r'^TRANS_%s' % f, k)]
        fam[f] = {'n': len(idx), 'lo': idx[0], 'hi': idx[-1]}
    d['fam'] = fam
    # W 块自证
    Wk = [k for k in en if k and k.startswith('TRANS_W')]
    blocks = collections.OrderedDict()
    suffix = {}
    for k in Wk:
        m = re.match(r'^TRANS_W(\d+)_(\d+)_(\d+)$', k)
        b = int(m.group(1))
        blocks.setdefault(b, []).append((int(m.group(2)), int(m.group(3))))
        suffix.setdefault(b, []).append(m.group(3))
    d['blocks'] = len(blocks)
    d['block_contig'] = (min(blocks) == 1 and max(blocks) - min(blocks) + 1 == len(blocks))
    bad = 0
    for b, v in blocks.items():
        nums = [x[0] for x in v]
        if nums != list(range(1, len(nums) + 1)):
            bad += 1
    d['bad_blocks'] = bad
    d['suffixes'] = dict(collections.Counter(x for v in suffix.values() for x in v))
    # 回声
    W = [ja[i] for i, k in enumerate(en) if k and k.startswith('TRANS_W')]
    T = [ja[i] for i, k in enumerate(en) if k and k.startswith('TRANS_T')]
    d['echo_W'] = sum(1 for i in range(1, len(W)) if W[i] == W[i - 1] or W[i] in W[i - 1].split('<br>'))
    d['echo_T'] = sum(1 for i in range(1, len(T)) if T[i] == T[i - 1] or T[i] in T[i - 1].split('<br>'))
    d['blank_frames'] = sum(1 for v in W + T if v and not re.sub(r'<[^>]+>', '', v.replace('<br>', '')).strip())
    d['prefix_growth'] = sum(1 for i in range(1, len(W)) if W[i].startswith(W[i - 1]) and W[i] != W[i - 1])
    # 标签
    tags = collections.Counter()
    for v in ja:
        tags.update(re.findall(r'<[^>]{1,32}>', v or ''))
    d['tags'] = dict(tags)
    # T 篇目（*_0000 = 标题行）
    d['T_titles'] = [ja[i] for i, k in enumerate(en) if k and re.match(r'^TRANS_T\d+_0000$', k)]
    # 成品
    raw = open(txt, 'rb').read()
    text = raw.decode('utf-8-sig')
    lines = text.rstrip('\n').split('\n')
    d['out_lines'] = len(lines)
    d['out_bytes'] = len(raw)
    d['first'] = lines[:2]
    d['last2'] = lines[-3:]
    d['period'] = text.count('。')
    d['lq'] = text.count('「')
    d['rq'] = text.count('」')
    d['ends_period'] = sum(1 for l in lines if l.endswith('。'))
    d['glossary_hits'] = [i for i, v in enumerate(ja) if v and re.search(r'用語|辞典|図鑑|ＷＯＲＤ|WORD', v)]
    out[tag] = d

print(json.dumps(out, ensure_ascii=False, indent=1))
