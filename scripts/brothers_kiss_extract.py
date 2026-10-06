#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ブラザーズ～恋するお兄さま＆もっと恋するお兄さま～  (Tiaramode, 2007, BGI/Ethornell)
全テキスト抽出ツール  —  PackFile(.arc) -> DSC(Huffman) -> V1命令列 -> 表示順

使い方:
    python brothers_kiss_extract.py <game_root_dir> <output.txt>
      game_root_dir : BGI.exe のあるフォルダ（data0100.arc 等が入っている場所）

抽出順（＝プレイ中の表示順）:
    main -> week01_01 … week02_08 -> week02_end -> 各END   （本編 "Suite"）
    続いて付録ディスク "Rhapsody"（もっと恋するお兄さま）の各ルート
"""
import struct, sys, os, re

# ---------------------------------------------------------------- PackFile
def arc_read(path):
    d = open(path, 'rb').read()
    if d[:12] != b'PackFile    ':
        raise ValueError('not PackFile: ' + path)
    count = struct.unpack_from('<I', d, 12)[0]
    ents, off = [], 16
    for _ in range(count):
        name = d[off:off+16].split(b'\x00')[0].decode('cp932', 'replace')
        o, s = struct.unpack_from('<II', d, off+16)
        ents.append((name, o, s))
        off += 32
    return d, ents, off

# ---------------------------------------------------------------- DSC (Huffman)
def dsc_decompress(data):
    if data[:16] != b'DSC FORMAT 1.00\x00':
        raise ValueError('not DSC')
    magic = struct.unpack_from('<H', data, 0)[0] << 16
    key = struct.unpack_from('<I', data, 0x10)[0]
    dec_count = struct.unpack_from('<I', data, 0x18)[0]

    def update_key():
        nonlocal key
        v0 = (20021 * (key & 0xFFFF)) & 0xFFFFFFFF
        v1 = (magic | (key >> 16)) & 0xFFFFFFFF
        v1 = (v1 * 20021 + key * 346) & 0xFFFFFFFF
        v1 = (v1 + (v0 >> 16)) & 0xFFFF
        key = ((v1 << 16) + (v0 & 0xFFFF) + 1) & 0xFFFFFFFF
        return v1 & 0xFF

    hcodes = []
    for i in range(512):
        depth = (data[0x20+i] - update_key()) & 0xFF
        if depth:
            hcodes.append((depth, i))
    hcodes.sort()
    ntotal = len(hcodes)

    hnodes = [None]*1023
    nidx = [[0]*512, [0]*512]
    next_idx, depth_nodes, depth, cbuf = 1, 1, 0, 0
    nidx[0][0] = 0
    n = 0
    while n < ntotal:
        hni = cbuf; cbuf ^= 1
        existed = 0
        while n < ntotal and hcodes[n][0] == depth:
            hnodes[nidx[hni][existed]] = (False, hcodes[n][1], 0, 0)
            n += 1; existed += 1
        create = depth_nodes - existed
        for i in range(create):
            hnodes[nidx[hni][existed+i]] = (True, 0, next_idx, next_idx+1)
            nidx[cbuf][i*2] = next_idx; next_idx += 1
            nidx[cbuf][i*2+1] = next_idx; next_idx += 1
        depth += 1; depth_nodes = create*2

    src = data[0x220:]
    bitpos = 0

    def nbit():
        nonlocal bitpos
        if bitpos >= len(src)*8:
            return -1
        b = (src[bitpos >> 3] >> (7-(bitpos & 7))) & 1
        bitpos += 1
        return b

    out = bytearray()
    for _ in range(dec_count):
        ni = 0
        while True:
            b = nbit()
            if b < 0:
                raise EOFError
            nd = hnodes[ni]
            ni = nd[2] if b == 0 else nd[3]
            if not hnodes[ni][0]:
                break
        code = hnodes[ni][1]
        if code >= 256:
            off = 0
            for _ in range(12):
                b = nbit()
                if b < 0:
                    break
                off = (off << 1) | b
            cnt = (code & 0xFF) + 2
            off += 2
            p = len(out) - off
            for _ in range(cnt):
                out.append(out[p]); p += 1
        else:
            out.append(code)
    return bytes(out)

# ---------------------------------------------------------------- script VM
V1_INSTS = {0x0000: 1, 0x0001: 1, 0x0002: 1, 0x0008: 1, 0x0009: 1, 0x000A: 1,
            0x0017: 1, 0x0019: 1, 0x003F: 1, 0x007B: 3, 0x007E: 1, 0x007F: 2}
FLUSH_OPS = {0x007e, 0x007f, 0x00fe, 0x01b5}
MSG_OPS = {0x0140, 0x0143, 0x0145}
CHOICE_OP = 0x0160
RUBY_OP = 0x014e
CALL_OP = 0x00f0          # スタック上の文字列＝スクリプト名 を読み込んで実行

def script_events(dec, encoding='cp932'):
    """1スクリプト -> [(kind, payload)]  kind: 'T'本文 / 'C'選択肢 / 'S'呼出"""
    n = len(dec)

    def cs(a):
        if not (0 <= a < n):
            return None
        e = dec.find(b'\x00', a)
        return dec[a:e] if e >= 0 else None

    ev = []
    stack, opts = [], []
    min_str = None
    prev_op = None
    pos = 0
    while pos + 4 <= n:
        if min_str is not None and pos >= min_str:
            break
        op = struct.unpack_from('<I', dec, pos)[0]
        start = pos
        pos += 4
        if op == 0x0003:
            if pos + 4 > n:
                break
            v = struct.unpack_from('<I', dec, pos)[0]; pos += 4
            stack.append(v)
            if prev_op == 0x0020:
                opts.append(v)
            if min_str is None or v < min_str:
                min_str = v
        elif op in MSG_OPS:
            if len(stack) >= 2:
                msg = cs(stack[-2]); stack.pop(); stack.pop()
            elif len(stack) == 1:
                msg = cs(stack[-1]); stack.pop()
            else:
                msg = None
            if msg:
                ev.append(('T', msg))
        elif op == CHOICE_OP:
            for v in opts:
                s = cs(v)
                if s:
                    ev.append(('C', s))
            opts = []; stack = []
        elif op == RUBY_OP:
            if len(stack) >= 2:
                stack.pop(); stack.pop()
        elif op in V1_INSTS:
            need = 4 * V1_INSTS[op]
            if pos + need > n:
                break
            vals = []
            for _ in range(V1_INSTS[op]):
                vals.append(struct.unpack_from('<I', dec, pos)[0]); pos += 4
            if op == 0x007f and vals:
                if min_str is None or vals[0] < min_str:
                    min_str = vals[0]
        else:
            if op == CALL_OP and stack:
                s = cs(stack[-1])
                if s:
                    ev.append(('S', s))
        if op in FLUSH_OPS:
            stack = []
        prev_op = op
        if pos <= start:
            break
    return ev

# ---------------------------------------------------------------- build
def collect(root):
    """ returns dict name -> events """
    ev = {}
    for fn in sorted(os.listdir(root)):
        if not fn.endswith('.arc'):
            continue
        # シナリオ／システムスクリプトのみ（sysgrp.arc は画像、data02xx/04xx は画像・音声）
        if not (fn.startswith('data01') or fn.startswith('sysprg') or fn.startswith('system')):
            continue
        p = os.path.join(root, fn)
        try:
            d, ents, base = arc_read(p)
        except Exception:
            continue
        for name, o, s in ents:
            blob = d[base+o:base+o+s]
            if blob[:16] != b'DSC FORMAT 1.00\x00':
                continue
            try:
                dec = dsc_decompress(blob)
            except Exception:
                continue
            try:
                ev[name] = script_events(dec)
            except Exception:
                ev[name] = []
    return ev

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    root = sys.argv[1]
    root_app = sys.argv[2] if len(sys.argv) > 2 else ''
    outpath = sys.argv[3] if len(sys.argv) > 3 else 'out.txt'

    ev_main = collect(root)
    ev_app = collect(root_app) if (root_app and os.path.isdir(root_app)) else {}
    ev_all = dict(ev_main)
    ev_all.update(ev_app)

    def lower_map(d):
        m = {}
        for k in d:
            m.setdefault(k.lower(), k)
        return m
    lo_main, lo_all = lower_map(ev_main), lower_map(ev_all)

    lines = []
    visited = set()

    def emit(name, table, lomap):
        if isinstance(name, bytes):
            name = name.decode('cp932', 'replace')
        if name not in table:
            name = lomap.get(name.lower(), name)
        if name in visited or name not in table:
            return
        visited.add(name)
        for k, v in table[name]:
            if k == 'T':
                lines.append(v)
            elif k == 'C':
                lines.append(v)
            elif k == 'S':
                emit(v, table, lomap)

    # ---- 本編 "Suite"（第1ディスクのみ。付録スクリプトへは踏み込まない） ----
    emit('main', ev_main, lo_main)
    main_lines = len(lines)

    # ---- 付録 "Rhapsody"（もっと恋するお兄さま・第2ディスク） ----
    for entry in ('appendix_so', 'appendix_se', 'appendix_su', 'appendix_yo',
                  'appendix_ka', 'appendix_harem', 'appendix_so_m', 'appendix_su_m',
                  'start_mama', 'start_mama_m', 'omakeadd', 'omakeadd2', 'winkappendix'):
        emit(entry, ev_all, lo_all)

    # ---- 未到達の実テキスト持ちスクリプトを数値順で補完 ----
    leftover = []
    for name in ev_all:
        if name in visited:
            continue
        if name.startswith('scene_') or name in ('main', 'makerlogo', 'omakesetup', 'omakesetup2'):
            continue
        if name.endswith('_old'):
            continue
        if any(k in ('T', 'C') for k, _ in ev_all[name]):
            leftover.append(name)

    def sortkey(x):
        mm = re.match(r'(\d+)', x)
        return (int(mm.group(1)) if mm else 10**9, x)
    leftover.sort(key=sortkey)
    for name in leftover:
        emit(name, ev_all, lo_all)

    # ---- 出力 ----
    # 《...》 は主人公名ハイライト用のマークアップ（本編では名前のみ表示）→ 括弧だけ除去
    clean = []
    main_clean = 0
    for i, raw in enumerate(lines):
        t = raw.decode('cp932', 'replace') if isinstance(raw, bytes) else raw
        t = t.replace('\r', '').replace('\n', '')
        t = t.replace('《', '').replace('》', '')
        if t.strip() == '':
            continue
        if i < main_lines:
            main_clean += 1
        clean.append(t)
    os.makedirs(os.path.dirname(os.path.abspath(outpath)), exist_ok=True)
    with open(outpath, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(clean) + '\n')

    print(f'files-used={len(visited)} lines={len(clean)} -> {outpath}')
    print(f'main_lines(1-{main_clean}) appendix_lines({main_clean+1}-{len(clean)})')
    print(f'leftover-with-text={len(leftover)} {leftover[:10]}')


if __name__ == '__main__':
    main()
