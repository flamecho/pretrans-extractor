# -*- coding: utf-8 -*-
"""とらぶるふぉうちゅんCOMPANY★はぴCURE (PS2, Primavera/Interchannel "nlib") 文本提取

PAC.BIN 结构（逆向所得，全部由 SLPM_666.26 的反汇编 + 闭合校验确认）:
  PAC.BIN = 若干 「minipack」顺序排列，每个 0x800 对齐
    minipack 头 = 12 字节记录数组（[u32 off][u32 size][u8 type][u8 0xFF?][u16 id]）
      记录 off/size 均相对 minipack 起点；末记录 off == size == minipack 总长（终止符）
    数据区自 0x200 起
  成员文件若以 b'LZS\\0' 开头 → LZSS 压缩：
    [4s 'LZS\\0'][u32 解压后长度][LZSS 流]
  LZSS（delzss.c，由 0x15A0F8 函数反汇编确认）:
    flag 字节 + 8 token，LSB 先行；bit=1 → 1 字节字面量；bit=0 → 2 字节：
      off = b0 | ((b1 & 0xF0) << 4)      # 4096 环内绝对位置
      len = (b1 & 0x0F) + 3
    环初值 0x00..0xFFED = 0x20，写指针初值 0xFEE
  脚本文件（TAK）字节码：
    0xAA <u16 msgid> <cp932 文本> 0x00 0x00      ← 一框一点击
    0xAB 00 00 00                                ← 点击/等待
"""
import os, struct, sys

SECTOR = 0x800


def lzs_decompress(data, usize):
    W = 4096
    win = bytearray([0x20]) * W
    win[0xFEE:] = bytes(0x1000 - 0xFEE)
    out = bytearray()
    pos = 0xFEE
    i = 0
    n = len(data)
    while i < n and len(out) < usize:
        flags = data[i]
        i += 1
        for k in range(8):
            if i >= n or len(out) >= usize:
                break
            if (flags >> k) & 1:
                b = data[i]
                i += 1
                out.append(b)
                win[pos & 0xFFF] = b
                pos += 1
            elif i + 1 < n:
                b0 = data[i]
                b1 = data[i + 1]
                i += 2
                off = b0 | ((b1 & 0xF0) << 4)
                ln = (b1 & 0x0F) + 3
                for j in range(ln):
                    x = win[(off + j) & 0xFFF]
                    out.append(x)
                    win[pos & 0xFFF] = x
                    pos += 1
                    if len(out) >= usize:
                        break
    return bytes(out)


def parse_pack(buf, s, maxrec=200):
    """buf 为整文件；返回 (recs, total) 或 None"""
    if s + 48 > len(buf):
        return None
    recs = []
    prev = 0
    for i in range(maxrec):
        o = s + i * 12
        if o + 12 > len(buf):
            return None
        a, b = struct.unpack('<II', buf[o:o + 8])
        if a == b and 0x1000 < a < 0x8000000:
            if len(recs) < 1:
                return None
            # 首成员必须是已知魔数，压掉误判
            mg = buf[s + recs[0][0]:s + recs[0][0] + 4]
            if mg not in (b'LZS\x00', b'IECS'):
                return None
            return (recs, a)
        if not (0x40 <= a < 0x8000000 and 0x10 < b < 0x8000000 and a > prev):
            return None
        recs.append((a, b, buf[o + 8:o + 12]))
        prev = a
    return None


def scan_packs(buf):
    packs = []
    for s in range(0, len(buf) - 0x400, SECTOR):
        r = parse_pack(buf, s)
        if r:
            packs.append((s, r[0], r[1]))
    return packs


def main():
    pac = sys.argv[1] if len(sys.argv) > 1 else '_work_thc/iso/PAC.BIN'
    outdir = sys.argv[2] if len(sys.argv) > 2 else '_work_thc/files'
    os.makedirs(outdir, exist_ok=True)
    buf = open(pac, 'rb').read()
    packs = scan_packs(buf)
    print('packs', len(packs), 'files', sum(len(p[1]) for p in packs))
    idx = 0
    stat = {}
    report = []
    for s, recs, tot in packs:
        for k, (off, size, meta) in enumerate(recs):
            if off + size > len(buf):
                continue
            d = buf[s + off:s + off + size]
            if d[:4] == b'LZS\x00':
                usize = struct.unpack('<I', d[4:8])[0]
                data = lzs_decompress(d[8:], usize)
                kind = 'LZS'
            else:
                data = d
                kind = d[:4].decode('latin1')
            stat[kind] = stat.get(kind, 0) + 1
            kana = 0
            try:
                t = data.decode('cp932', 'replace')
                kana = sum(1 for c in t if '\u3040' <= c <= '\u30ff')
            except Exception:
                pass
            if b'\xaa\x00' in data:
                fn = os.path.join(outdir, '%05d_%08x_%02d.bin' % (idx, s, k))
                with open(fn, 'wb') as w:
                    w.write(data)
            report.append((idx, s, k, off, size, meta.hex(), kind, len(data), kana))
            idx += 1
    print(stat)
    with open(os.path.join(outdir, 'index.tsv'), 'w', encoding='utf-8') as w:
        w.write('idx\tpack\tfile\toff\tsize\tmeta\tkind\tdeclen\tkana\n')
        for r in report:
            w.write('\t'.join(str(x) for x in r) + '\n')


if __name__ == '__main__':
    main()
