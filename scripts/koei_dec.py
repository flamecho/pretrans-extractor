# -*- coding: utf-8 -*-
"""アンジェリーク エトワール (PS2) PACK 成员解压 —— 由 SLPM 0x142c80 (type1) 反编译还原

格式 (type 1):
  [u32 maskBits][mask: (maskBits+7)>>3 字节][交错: 字面量 1 字节 / 匹配 2 字节]
  掩码按字节 LSB 先，bit=1 -> 字面量, bit=0 -> 匹配
  匹配 token (u16 LE): dist = token>>4 (0=结束), len = (token&0xF)+2
  源 = 4096 环形缓冲，写指针从 1 起（位置 p 对应 out[p-1]）
"""
import struct, sys
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

def dec_type1(src, out_len=None):
    maskbits = struct.unpack('<I', src[:4])[0]
    if maskbits == 0 or maskbits > 8 << 20:
        raise ValueError('bad maskbits %d' % maskbits)
    mlen = (maskbits + 7) >> 3
    if 4 + mlen > len(src):
        raise ValueError('mask overrun')
    mask = src[4:4 + mlen]
    pos = 4 + mlen
    out = bytearray()
    ring = bytearray(4096)
    w = 1
    n = len(src)
    for bi in range(maskbits):
        if out_len is not None and len(out) >= out_len:
            break
        bit = (mask[bi >> 3] >> (bi & 7)) & 1
        if bit:
            if pos >= n: break
            b = src[pos]; pos += 1
            out.append(b); ring[w] = b
            w = (w + 1) & 0xfff
        else:
            if pos + 1 >= n: break
            tok = struct.unpack('<H', src[pos:pos + 2])[0]; pos += 2
            d = tok >> 4
            if d == 0: break
            ln = (tok & 0xF) + 2
            for _ in range(ln):
                b = ring[d & 0xfff]
                out.append(b); ring[w] = b
                d = (d + 1) & 0xfff; w = (w + 1) & 0xfff
    return bytes(out), pos

if __name__ == '__main__':
    sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
    from etoile_unpack import load_pair, parse_pack
    sizes, ents, data = load_pair(os.path.join(VNTRANS_HOME, '_src_etoile/DATA01'))
    ok = 0; tot = 0; bad = 0
    for i, (o, s) in enumerate(ents):
        b = data[o:o + s]
        if b[:4] != b'PACK':
            continue
        h, mem = parse_pack(b)
        for nm, moff, st, dc, sp in mem:
            if sp != 1:
                continue
            tot += 1
            try:
                r, _ = dec_type1(b[moff:moff + st], dc)
            except Exception as e:
                bad += 1; continue
            if len(r) == dc:
                ok += 1
    print('DATA01 step=1 members: total=%d exact=%d err=%d' % (tot, ok, bad))
    # 具体样本
    for idx in (47, 52, 6):
        o, s = ents[idx]; b = data[o:o + s]
        h, mem = parse_pack(b)
        for nm, moff, st, dc, sp in mem:
            if nm == 'index.lst':
                r, used = dec_type1(b[moff:moff + st], dc)
                print('--- #%d %s st=%d dc=%d -> got=%d used=%d' % (idx, nm, st, dc, len(r), used))
                print(r.decode('cp932', 'replace'))
