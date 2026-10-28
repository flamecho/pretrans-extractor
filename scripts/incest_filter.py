#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""INNOCENT INCEST —— XP3 filter 解密（依据 sindata.tpm rva 0x1000 反汇编）

filter（对 info 结构体，+0xc=buf, +0x10=len, +0x14=hash32）:
  eax = hash ^ 0xF6D2B397
  for i in range(len):
      cl = (i&3)*8
      b = buf[i]
      b = (b - ((0xF53A7AC2 >> cl) & 0xff)) & 0xff
      b = b ^ ((eax >> cl) & 0xff)
      b = (b + ((0xDC98DACB >> cl) & 0xff)) & 0xff
      b = b ^ (0x18 if (i&3)==0 else 0)
      buf[i] = b
用法:
  python scripts/incest_filter.py try       # 用 hash=adlr / 0 直接试
  python scripts/incest_filter.py lane      # 逐 lane 256 值统计求解 + adler 校验
  python scripts/incest_filter.py dump <name> <outfile>   # 解密写出
"""
import struct, zlib, sys, os

PATH = '_work_incest/data.xp3'
S = [(0xF53A7AC2 >> (l * 8)) & 0xff for l in range(4)]
A = [(0xDC98DACB >> (l * 8)) & 0xff for l in range(4)]
C = [0x18, 0, 0, 0]


def load_idx(path=PATH):
    d = open(path, 'rb').read()
    off = struct.unpack_from('<Q', d, 0x0b)[0]
    raw = d[off:]
    k = next(i for i in range(64) if raw[i] == 0x78 and raw[i + 1] in (1, 0x5e, 0x9c, 0xda))
    idx = zlib.decompressobj().decompress(raw[k:])
    items, q = [], 0
    while q + 12 <= len(idx) and idx[q:q + 4] == b'File':
        sz = struct.unpack_from('<Q', idx, q + 4)[0]
        pl = idx[q + 12:q + 12 + sz]
        a, name, segs, adlr, iflag = 0, None, [], None, 0
        while a + 12 <= len(pl):
            t = pl[a:a + 4]
            s = struct.unpack_from('<Q', pl, a + 4)[0]
            sp = pl[a + 12:a + 12 + s]
            if t == b'info':
                iflag = struct.unpack_from('<I', sp, 0)[0]
                name = sp[22:22 + struct.unpack_from('<H', sp, 20)[0] * 2].decode('utf-16-le', 'replace')
            elif t == b'segm':
                sf, o, os_, cs = struct.unpack_from('<IQQQ', sp, 0)
                segs.append((sf, o, os_, cs))
            elif t == b'adlr':
                adlr = struct.unpack_from('<I', sp, 0)[0]
            a += 12 + s
        items.append((name, iflag, segs, adlr))
        q += 12 + sz
    return d, items


def cipher(d, it):
    """取条目密文（已 zlib 解压，未过 filter）"""
    buf = b''
    for sf, o, os_, cs in it[2]:
        buf += zlib.decompress(d[o:o + cs]) if sf & 0xff else d[o:o + cs]
    return buf


def dec(buf, key):
    """key = hash ^ 0xF6D2B397 的 4 字节；key 为 None 时逐 lane 原始字节"""
    n = len(buf)
    out = bytearray(n)
    kb = [(key >> (l * 8)) & 0xff for l in range(4)]
    for i in range(n):
        l = i & 3
        x = (buf[i] - S[l]) & 0xff
        x ^= kb[l]
        x = (x + A[l]) & 0xff
        x ^= C[l]
        out[i] = x
    return bytes(out)


TBL = {}
for l in range(4):
    for k in range(256):
        TBL[(l, k)] = bytes(
            ((((x - S[l]) & 0xff) ^ k) + A[l]) & 0xff ^ C[l] for x in range(256))


def dec_fast(buf, kb):
    out = bytearray(len(buf))
    for l in range(4):
        t = TBL[(l, kb[l])]
        seg = buf[l::4]
        out[l::4] = seg.translate(t)
    return bytes(out)


# ---- SJIS 文本可信度评分 ----
OK = bytearray(256)
for _b in list(range(0x20, 0x7f)) + list(range(0x81, 0xa0)) + list(range(0xa1, 0xe0)) + list(range(0xe0, 0xfd)):
    OK[_b] = 1
OK[0x09] = OK[0x0a] = OK[0x0d] = 1


def score_lane(buf, l):
    """返回 (best_k_list, 每条 lane 的 max 命中率)"""
    res = []
    seg = buf[l::4]
    for k in range(256):
        o = seg.translate(TBL[(l, k)])
        hit = sum(OK[b] for b in o)
        res.append((hit / len(o), k))
    res.sort(reverse=True)
    return res


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'try'
    d, items = load_idx()
    sel = [it for it in items if it[0].startswith('scenario/') and it[2][0][0] == 1]
    if cmd == 'try':
        for it in sel[:4]:
            c = cipher(d, it)
            for h in (it[3], 0, it[3] ^ 0xffffffff):
                p = dec_fast(c, [(h ^ 0xF6D2B397) >> (l * 8) & 0xff for l in range(4)])
                ok = (zlib.adler32(p) & 0xffffffff) == it[3]
                print('%-24s hash=%08x adler_ok=%s head=%r' % (it[0], h, ok, p[:24]))
    elif cmd == 'lane':
        for it in sel[:3]:
            c = cipher(d, it)
            print('== %s  len=%d adlr=%08x' % (it[0], len(c), it[3]))
            kb = []
            for l in range(4):
                r = score_lane(c, l)
                kb.append(r[0][1])
                print('   lane%d: top3 %s' % (l, ['k=%02x hit=%.3f' % (k, s) for s, k in r[:3]]))
            h = 0
            for l in range(4):
                h |= (kb[l] ^ ((0xF6D2B397 >> (l * 8)) & 0xff)) << (l * 8)
            p = dec_fast(c, [(h ^ 0xF6D2B397) >> (l * 8) & 0xff for l in range(4)])
            print('   derived hash=%08x adler_ok=%s' % (h, (zlib.adler32(p) & 0xffffffff) == it[3]))
            print('   head=%r' % p[:80])
    elif cmd == 'dump':
        name, outf = sys.argv[2], sys.argv[3]
        it = [x for x in items if x[0] == name][0]
        c = cipher(d, it)
        kb = [score_lane(c, l)[0][1] for l in range(4)]
        p = dec_fast(c, kb)
        open(outf, 'wb').write(p)
        print('-> %s  adler_ok=%s' % (outf, (zlib.adler32(p) & 0xffffffff) == it[3]))


main()
