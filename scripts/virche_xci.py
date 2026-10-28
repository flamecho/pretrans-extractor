#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重打包 XCI（封装头不自洽）→ 抽 NCA，带「数据起点自证」。

与 scripts/xci_hfs0.py 的差别：那份用 `filesize − Σsizes` 反推数据起点，
**当 XCI 尾部还挂着别的分区（本例尾部 4.29 GB 不是填充）时会整体偏 4 GB**，
导出的 NCA 头解不开（nstool 报 `Input file type was undetermined`）。

本脚本改为：
  ① 找到含 .nca 的 HFS0；
  ② 候选数据起点 = HFS0 起点 + 0x8000（本组两个重打包 XCI 实测一致）；
     否则在 [+0x1000, +0x200000] 内按 0x200 步长扫 **NCA3 头**（XTS 解 0x200 处魔数自证）；
  ③ 命中后用该起点按 sizes 顺序导出，并核对最后一个文件末端 + 尾部剩余量。
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import switch_nca as SN

ENTRY = 0x40


def find_hfs0(buf, lim):
    out, i = [], 0
    while True:
        j = buf.find(b'HFS0', i, lim)
        if j < 0:
            break
        num, strsz = struct.unpack_from('<II', buf, j + 4)
        if num <= 4096 and strsz <= 1 << 20 and j + 0x10 + num * ENTRY + strsz <= len(buf):
            st = j + 0x10 + num * ENTRY
            p, names, sizes = st, [], []
            ok = True
            for _ in range(num):
                e = buf.find(b'\x00', p, st + strsz + 1)
                if e < 0:
                    ok = False
                    break
                names.append(buf[p:e].decode('utf-8', 'replace'))
                p = e + 1
            if ok and any(n.endswith('.nca') for n in names):
                for k in range(num):
                    # ★ 尺寸是 **u64**（+0x08）；只取低 32 位会把 >4 GB 的 NCA 截断，
                    #   本项目实测：低 32 位 0xAF074000 / 完整 0x1AF074000
                    sizes.append(struct.unpack_from('<Q', buf, j + 0x10 + k * ENTRY + 0x08)[0])
                out.append((j, num, strsz, names, sizes))
        i = j + 1
    return out


def nca_ok(f, off, hk1, hk2):
    """★ NCA 头的 XTS tweak 基准是 **NCA 自身**（=0），不是容器绝对偏移；
    HFS0 数据起点常未 0x200 对齐（本例 0x1F022），拿它当 tweak 会解错。"""
    f.seek(off)
    d = f.read(0x400)
    if len(d) < 0x400:
        return False
    return SN.xts_decrypt(hk1, hk2, 0, d)[0x200:0x204] == b'NCA3'


def main():
    path = sys.argv[1]
    outdir = sys.argv[sys.argv.index('--extract') + 1] if '--extract' in sys.argv else None
    keys = SN.load_keys('_sw/prod_fixed.keys')
    hk1 = bytes.fromhex(keys['header_key'][:32])
    hk2 = bytes.fromhex(keys['header_key'][32:64])
    f = open(path, 'rb')
    f.seek(0, 2)
    fs = f.tell()
    f.seek(0)
    buf = f.read(min(fs, 64 << 20))
    hits = find_hfs0(buf, len(buf))
    print('%s  %s B  HFS0 候选 %d' % (path, format(fs, ','), len(hits)))
    if not hits:
        return 1
    off, num, strsz, names, sizes = hits[0]
    print('  @%#x  %d 项  names=%s' % (off, num, names[:3]))

    cand = [off + 0x8000]
    data = None
    for c in cand:
        if nca_ok(f, c, hk1, hk2):
            data = c
            break
    if data is None:
        for c in range(off + 0x1000, off + 0x200000, 0x200):
            if nca_ok(f, c, hk1, hk2):
                data = c
                break
    if data is None:
        print('✗ 数据起点未自证（NCA3 头未命中）')
        return 1
    total = sum(sizes)
    print('  数据起点 = %#x（NCA3 头自证） Σsize=%s  末端=%#x  文件=%#x  尾部剩 %#x'
          % (data, format(total, ','), data + total, fs, fs - data - total))

    if outdir:
        os.makedirs(outdir, exist_ok=True)
        cur = data
        for nm, sz in zip(names, sizes):
            if nm.endswith('.nca'):
                f.seek(cur)
                left = sz
                dst = os.path.join(outdir, nm)
                with open(dst, 'wb') as fo:
                    while left > 0:
                        b = f.read(min(1 << 24, left))
                        if not b:
                            break
                        fo.write(b)
                        left -= len(b)
                print('  导出 %s (%s B)' % (nm, format(sz, ',')))
            cur += sz
    return 0


if __name__ == '__main__':
    sys.exit(main())
