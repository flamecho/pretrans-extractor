#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Uragiri wa Boku no Namae o Shitteiru (PS2, Design Factory / Otomate 2010)
PETA(PTD) → YKLZ → JRS 字节码 → 正文。

链路:
  ISO9660 → UB_SPT.PTD (PETA, 索引区加密 = SBOX[b ^ t], t 每字节 -1)
    → 条目 [u32 off][u32 size][u32 flag][u32 0][name 0x50] (0x10 对齐扫描)
    → YKLZ (LZSS, shift=param-8) 解压 → *.JRS
  JRS: 0x00 magic 8f83dbcf / 0x14 code / 0x18 text / 0x1c A表 / 0x20 B表
    0x40 SBOX(256B)，正文池 = pool[i] = SBOX[enc[i] ^ t], t 每字节 -1
    A 表(u16) = 消息表：每条 = 一次点击，偏移必落串首（L1 自定界）
    B 表(u16) = 全部串引用（资源 / 名札 / 正文）
    代码流以 0x40 结束语句；`7f <u16>` 引用 A 索引（L0），`53 <u16>` 引用 B 名札

用法:
  python scripts/ura_ptd_jrs.py unpack <UB_SPT.PTD> <outdir>
  python scripts/ura_ptd_jrs.py build  <outdir> <out.txt>
"""
import struct, sys, os, re, glob

FIX = {'㌔': '祇', '㍉': '泠'}          # 字体自定槽 (0x8760/0x875F)
SKIP_FILES = {'SC4.JRS', 'SCENARIO_DEBUG.JRS', 'SC5461.JRS'}
DROP = {'攻撃', '逃げる', '防御', '必殺', 'アイテムを使用する', 'アイテムを使用しない'}


def yklz(data):
    if len(data) < 16 or data[:4] != b'YKLZ':
        return data
    param = data[7]
    shift = param - 8 if param >= 8 else 4
    mask = (1 << shift) - 1
    size = struct.unpack_from('<I', data, 8)[0]
    src = 0x10
    out = bytearray()
    while len(out) < size and src < len(data):
        flags = data[src]; src += 1
        for _ in range(8):
            if len(out) >= size or src >= len(data):
                break
            isref = (flags & 0x80) != 0
            flags = (flags << 1) & 0xFF
            if not isref:
                out.append(data[src]); src += 1
            else:
                if src + 1 >= len(data):
                    break
                b1 = data[src]; b2 = data[src + 1]; src += 2
                ln = (b1 >> shift) + 3
                off = (((b1 & mask) << 8) | b2) + 1
                st = len(out) - off
                for i in range(ln):
                    out.append(0 if st + i < 0 else out[st + i])
    return bytes(out)


def peta_entries(d):
    ds, ixsz, ixoff, cnt = struct.unpack_from('<4I', d, 4)
    sbox = d[0x20:0x120]
    idx = bytearray(); t = 0
    for b in d[ixoff:]:
        idx.append(sbox[b ^ t]); t = (t - 1) & 0xFF
    idx = bytes(idx)
    recs = []; seen = set()
    for p in range(0, min(len(idx), ds - ixoff), 0x10):
        if p + 0x50 > len(idx):
            break
        off, size, flag, pad = struct.unpack_from('<4I', idx, p)
        if off % 0x800 or size == 0 or size > 0x200000:
            continue
        if off + size > len(d):
            continue
        nm = idx[p + 0x10:p + 0x50].split(b'\0')[0]
        if len(nm) < 3 or not all(32 <= c < 127 for c in nm):
            continue
        if not (b'.' in nm or b'/' in nm):
            continue
        s = nm.decode()
        k = (off, size, s)
        if k in seen:
            continue
        seen.add(k); recs.append((off, size, flag, s))
    return recs


def unpack(src, outdir):
    d = open(src, 'rb').read()
    recs = peta_entries(d)
    os.makedirs(outdir, exist_ok=True)
    for off, size, flag, nm in recs:
        open(os.path.join(outdir, nm.replace('/', '_')), 'wb').write(yklz(d[off:off + size]))
    print('entries %d -> %s' % (len(recs), outdir))


def parse(f):
    d = open(f, 'rb').read()
    h = struct.unpack_from('<10I', d, 0)
    A = struct.unpack_from('<%dH' % ((h[8] - h[7]) // 2), d, h[7])
    B = struct.unpack_from('<%dH' % ((h[9] - h[8]) // 2), d, h[8])
    sbox = d[0x40:0x140]
    pool = bytearray(); t = 0
    for b in d[h[6]:]:
        pool.append(sbox[b ^ t]); t = (t - 1) & 0xFF
    pool = bytes(pool)

    def s(o):
        return pool[o:pool.find(b'\0', o)].decode('cp932', 'replace')
    return [s(a) for a in A], [s(b) for b in B]


def key(f):
    n = os.path.basename(f)[:-4]
    m = re.match(r'SC(\d+)$', n)
    return (int(m.group(1)[0]), int(m.group(1)[1:] or 0), n) if m else (99, 0, n)


def clean(s):
    s = s.replace('\r', '').rstrip('\n')
    s = s.replace('\n\u3000', '').replace('\n', '')
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r'\{?\[([^\[\]:{}]+):([^\[\]:{}]+)\]\}?', r'\1', s)
        s = re.sub(r'\{?\[([^\[\]{}]+)\]\}?', r'\1', s)
        s = re.sub(r'\{([^{}]+)\}', r'\1', s)
    for k, v in FIX.items():
        s = s.replace(k, v)
    return s.strip()


def build(indir, out):
    lines = []
    for f in sorted(glob.glob(os.path.join(indir, '*.JRS')), key=key):
        if os.path.basename(f) in SKIP_FILES:
            continue
        for s in parse(f)[0]:
            t = clean(s)
            if not t or t in DROP:
                continue
            lines.append(t)
    open(out, 'w', encoding='utf-8-sig', newline='\n').write('\n'.join(lines) + '\n')
    print('lines %d -> %s' % (len(lines), out))


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'unpack':
        unpack(sys.argv[2], sys.argv[3])
    elif cmd == 'build':
        build(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit(__doc__)
