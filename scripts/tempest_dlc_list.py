#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""逐个清点 even if TEMPEST 宵闇にかく語りき魔女 的 12 个 DLC（NS-JP）。

对每个 DLC NSP：
  1. 列 romfs，按类别计数（scb 脚本 / dds 贴图 / opus 语音）；
  2. 取 script~NN_01_dlc.scb 解包 → 解压 → 收集场景标签与文本 ID 引用；
  3. 用本体 static~NN_01 池里的 ID 集合判定引用能否解析
     （能解析＝跨章节回想引用；不能解析且属 00NN 命名空间＝DLC 专属文本表，本体内不存在）；
  4. 明确判定该 DLC 是否携带文本池（BIN_ / static~*.bea）。

用法: python scripts/tempest_dlc_list.py <DLC 目录> <本体已解包目录> [--json out.json]
"""
import sys, os, re, glob, json, struct

import zstandard

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nsp_plainromfs as W4

IDRE = re.compile(r'^\d{4}_\d{4}[a-z_]?$')
LAB = re.compile(r'^\d\d_\d\d_dlc_\d+$')


def scne_scb(b):
    j = b.find(b'\x28\xb5\x2f\xfd')
    if j < 0:
        return b''
    return zstandard.ZstdDecompressor().decompress(b[j:], max_output_size=64 << 20)


def base_ids(srcdir):
    """本体各 static~NN_01 池里的全部文本 ID 集合。"""
    ids = set()
    for p in glob.glob(os.path.join(srcdir, '**', 'static~*.bin.nx.bea'), recursive=True):
        b = open(p, 'rb').read()
        j = b.find(b'\x28\xb5\x2f\xfd')
        if j < 0:
            continue
        d = zstandard.ZstdDecompressor().decompress(b[j:], max_output_size=256 << 20)
        if d[:4] != b'BIN_':
            continue
        n = struct.unpack_from('<I', d, 0x0C)[0]
        base = struct.unpack_from('<I', d, 0x18)[0]
        if 0x1C + n * 4 != base:
            continue
        for o in struct.unpack_from('<%dI' % n, d, 0x1C):
            s = d[base + o:d.index(b'\x00', base + o)].decode('utf-8', 'replace')
            if IDRE.match(s):
                ids.add(s)
    return ids


def main():
    dlcdir = sys.argv[1]
    basedir = sys.argv[2]
    js = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
    bids = base_ids(basedir)
    print('[i] 本体文本 ID 集合 %d 条' % len(bids))

    out = []
    names_all = sorted(os.listdir(dlcdir))  # 目录名含 [ ]，不能用 glob（会被当字符类）
    for nsp in [os.path.join(dlcdir, x) for x in names_all if 'DLC' in x and x.endswith('.nsp')]:
        tag = re.search(r'\[(DLC \d+)\]', nsp).group(1)
        n, v, comp = W4.open_nsp(nsp)
        if comp[0] or comp[1]:
            raise SystemExit('压缩段')
        files, fd = W4.parse_romfs(v)
        names = [f[0] for f in files]
        scb = [x for x in names if '/script~' in x and x.endswith('.nx.bea')]
        dds = [x for x in names if x.endswith('.dds.nx.bea')]
        opus = [x for x in names if x.startswith('stream/')]
        pools = [x for x in names if 'static~' in x or x.endswith('/static.nx.bea')]
        chaps, refs = [], set()
        for nm in scb:
            rec = next(f for f in files if f[0] == nm)
            b = b''.join(v.read(rec[1] + k, min(1 << 23, rec[2] - k))
                         for k in range(0, rec[2], 1 << 23))
            d = scne_scb(b)
            ss = [x.decode('utf-8', 'replace') for x in d.split(b'\x00') if x]
            chaps.append(os.path.basename(nm).replace('script~', '').replace('_dlc.scb.nx.bea', ''))
            for s in ss:
                if IDRE.match(s):
                    refs.add(s)
        own = sorted({r[:4] for r in refs if r[:4].startswith('00') and r not in bids})
        hit = sorted(refs & bids)
        rec = dict(tag=tag, file=os.path.basename(nsp), scb=chaps, n_scb=len(scb),
                   n_dds=len(dds), n_opus=len(opus), n_pool=len(pools),
                   refs=len(refs), resolved=len(hit), own_ns=own,
                   own_refs=sorted(r for r in refs if r not in bids))
        out.append(rec)
        print('%s  脚本%s  贴图%2d  语音%3d  文本池%d | 引用ID %3d（本体可解析 %3d，DLC专属 %s %d）'
              % (tag, ','.join(chaps), len(dds), len(opus), len(pools), len(refs), len(hit),
                 ','.join(own) or '-', len(rec['own_refs'])))

    if js:
        json.dump(out, open(js, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('[i] -> %s' % js)


if __name__ == '__main__':
    main()
