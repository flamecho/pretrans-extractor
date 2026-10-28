# -*- coding: utf-8 -*-
"""クレプシドラ ARC2 + LZSS 解压器

格式结论（逆向所得，241/245 文件解出合法 CP932，长度与索引 usize 全部吻合）：
  ARC2 容器: [4s magic][u32 count][u32 off0][u32 usize0] + (count-1) 条索引 + 数据区
    索引记录: [u8 namelen][namelen 字节 名字^0xFF][u32 off][u32 usize]
    第 1 个文件的 off/usize 存在 16 字节头里，其名字是索引区末尾那条只有名字的记录。
  LZSS 流:
    flag 字节 + 8 个 token（flag 按 LSB 先行取位）
    bit=0 -> 1 字节字面量
    bit=1 -> 2 字节 (b0,b1)，先各自 ^0xFF 得 n0,n1:
        len      = (n1 & 0x0F) + 3                       (3..18)
        src_mod  = (((n1 & 0xF0) << 4) | n0) + 18        (mod 4096)
        dist     = (已输出长度 - src_mod) & 0xFFF        (0 视为 4096)
        从 dist 处逐字节复制 len 字节（允许重叠）
"""
import struct


def parse_arc2(buf):
    """返回 [(name, off, usize)]"""
    magic = buf[:4]
    assert magic == b'ARC2', magic
    count, off0, us0 = struct.unpack('<III', buf[4:16])
    recs = []
    pos = 16
    while len(recs) < count - 1:
        L = buf[pos]
        nm = bytes(b ^ 0xFF for b in buf[pos+1:pos+1+L])
        off, us = struct.unpack('<II', buf[pos+1+L:pos+1+L+8])
        recs.append((nm.decode('cp932'), off, us))
        pos += 1 + L + 8
    # 索引区末尾（数据区之前）剩下的是第一个文件的名字
    rest = buf[pos:off0]
    name0 = None
    if rest and rest[0] == len(rest) - 1:
        name0 = bytes(b ^ 0xFF for b in rest[1:]).decode('cp932')
    recs.insert(0, (name0, off0, us0))
    return recs


def lzss_decompress(blob):
    out = bytearray()
    pos, n = 0, len(blob)
    while pos < n:
        flag = blob[pos]; pos += 1
        for b in range(8):
            if pos >= n:
                break
            if (flag >> b) & 1:
                if pos + 1 >= n:
                    pos = n
                    break
                n0 = blob[pos] ^ 0xFF
                n1 = blob[pos+1] ^ 0xFF
                pos += 2
                ln = (n1 & 0x0F) + 3
                src_mod = ((((n1 & 0xF0) << 4) | n0) + 18) & 0xFFF
                dist = (len(out) - src_mod) & 0xFFF
                if dist == 0:
                    dist = 4096
                for _ in range(ln):
                    i = len(out) - dist
                    out.append(out[i] if 0 <= i < len(out) else 0)
            else:
                out.append(blob[pos]); pos += 1
    return bytes(out)


def extract(path):
    buf = open(path, 'rb').read()
    recs = parse_arc2(buf)
    inv = bytes(b ^ 0xFF for b in buf)
    files = []
    for i, (name, off, us) in enumerate(recs):
        end = recs[i+1][1] if i+1 < len(recs) else len(buf)
        comp = inv[off:end]
        # clen == usize ⇒ 未压缩原样存储（本作 4 个：ハートシーク.adv 与 3 个 PNG）
        data = comp if len(comp) == us else lzss_decompress(comp)
        files.append((name, data, us))
    return files


if __name__ == '__main__':
    import sys, os
    src = sys.argv[1]
    dst = sys.argv[2]
    os.makedirs(dst, exist_ok=True)
    for name, data, us in extract(src):
        safe = name.replace('\\', '__').replace('/', '__')
        open(os.path.join(dst, safe), 'wb').write(data)
        flag = '' if len(data) == us else '  !! usize %d' % us
        print('%-46s %8d%s' % (name, len(data), flag))
