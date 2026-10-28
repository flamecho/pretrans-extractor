"""XCI (HFS0) 手工解析/抽 NCA —— 专治重打包 XCI 的「封装头不自洽」。

现象：`hactool -t xci` 直接报 `XCI partition is corrupt!`（update/normal 变成 17 B 存根、
`rom_area_start_page` 与 secure 实起点不符）。数据本身没坏，只是封装层对不上。

本工具**只读 HFS0 结构**，按实测规律定位并抽取 NCA：
  ① 扫描前 64 MB 里所有 `HFS0` 魔数；
  ② 挑「名字表里含 `.nca`」的那个（真正的 secure 分区；其偏移常**未 0x200 对齐**，如 0x17022）；
  ③ 条目长 0x40，`+0x08` 是文件大小；名字表 = 头部 + 0x10 + n×0x40，按 NUL 顺序切；
  ④ 数据起点用**精确闭合**反推：`data_start = filesize − Σ(sizes)`（校验该处前 0x20 B 非全零）；
  ⑤ 按 sizes 顺序把 NCA 原样拷出，交给 `hactool -t nca` 继续。

用法：
    python scripts/xci_hfs0.py <x.xci>                 # 只列分区与 NCA
    python scripts/xci_hfs0.py <x.xci> --extract DIR   # 导出 NCA 到 DIR
    python scripts/xci_hfs0.py <x.xci> --at 0x17018200 # 显式指定数据起点（多分区/尾部填充时）

⚠ **已知不可靠的情形**（2026-10-26 实测）：一个 XCI 里含**多个分区 + 尾部大量填充**时
（如 My9Swallows TOPSTARS LEAGUE：`0x17018000` 处是 999 MB 的分区、另有更大的分区靠近文件尾），
「Σsize 最大的 HFS0 + 闭合」与「rom_area 头部」会给出**不同**答案，工具无法自动判对。
此时要么 `--at <hex>` 显式给起点，要么改用 `scripts/nca_romfs.py`（W1 在 My9Swallows 上验证过，就地读）。
单分区的普通重打包件（如 Honey Vibes）本工具是准的。
"""
import os
import struct
import sys

SCAN = 64 << 20      # HFS0 头都在前 64 MB
ENTRY = 0x40


def cand_names(buf, off):
    """尝试把 off 处的 HFS0 名字表按 NUL 切开；返回 (num, strsz, names, sizes)。"""
    if buf[off:off + 4] != b'HFS0':
        return None
    num, strsz = struct.unpack_from('<II', buf, off + 4)
    if num > 4096 or strsz > 1 << 20:
        return None
    st = off + 0x10 + num * ENTRY
    if st + strsz > len(buf):
        return None
    names, sizes = [], []
    p = st
    for _ in range(num):
        e = buf.find(b'\x00', p, st + strsz + 1)
        if e < 0:
            break
        names.append(buf[p:e].decode('utf-8', 'replace'))
        p = e + 1
    for i in range(num):
        got = struct.unpack_from('<IIQ', buf, off + 0x10 + i * ENTRY)
        sizes.append(got[2])
    return num, strsz, names, sizes


def find_secure(buf):
    hits = []
    i = 0
    lim = len(buf)                      # ★必须扫全文：secure 分区可能远离文件头
    while True:                         #   （My9Swallows 的 secure 在 0x17018000，只扫前 64 MB 就会
        j = buf.find(b'HFS0', i, lim)   #    误取到 0xf200 那个 229 项 / 339 MB 的分区）
        if j < 0:
            break
        r = cand_names(buf, j)
        if r and any(n.endswith('.nca') for n in r[2]):
            hits.append((j,) + r)
        i = j + 4
    return hits


def main():
    path = sys.argv[1]
    outdir = sys.argv[sys.argv.index('--extract') + 1] if '--extract' in sys.argv else None
    with open(path, 'rb') as f:
        buf = f.read()
    fs = len(buf)

    hits = find_secure(buf)
    print(f'{path}  {fs:,} B')
    print(f'含 .nca 的 HFS0 候选 {len(hits)} 个:')
    for off, num, strsz, names, sizes in hits:
        print(f'  @{off:#x}  {num} 项  名字表 {strsz:#x}')
    if not hits:
        print('没找到 secure 分区')
        return 1
    # 真 secure 分区装的是整个游戏 ⇒ 取 Σsize 最大的那个候选
    hits.sort(key=lambda h: -sum(h[4]))
    off, num, strsz, names, sizes = hits[0]

    total = sum(sizes)

    # 数据起点候选（**不能只用闭合反推**）：
    #   ① secure HFS0 自身头部推出的数据区 = off + 0x10 + n*0x40 + strsz   ← 正规
    #   ② gamecard 头 @0x104 rom_area_start_page*0x200
    #   ③ filesize − Σsizes —— 仅「尾部无填充」时精确
    # 反例：My9Swallows TOPSTARS LEAGUE 尾部有 ~339 MB 填充、且存在 229 项/339 MB 的伪 HFS0，
    #       ①③ 都会错（真值 0x17018200）⇒ 这类包请显式 `--at 0x17018200`，或用
    #       `scripts/nca_romfs.py`（W1 已在 My9Swallows 上验证，能就地读 nsp/xci）。
    hdr_data = off + 0x10 + num * ENTRY + strsz
    cand = [('hfs0_hdr', hdr_data), ('filesize-Σsizes', fs - total)]
    if buf[0x100:0x104] == b'HEAD':
        page = struct.unpack_from('<I', buf, 0x104)[0]
        if page:
            cand.append(('rom_area_start_page', page * 0x200))

    forced = None
    if '--at' in sys.argv:
        forced = int(sys.argv[sys.argv.index('--at') + 1], 16)
        cand.insert(0, ('--at 指定', forced))

    print()
    for how, c in cand:
        ok = c + total <= fs
        print(f'候选 [{how}] {c:#x}  装得下={ok}  前20B非零={any(buf[c:c + 0x20])}'
              + (f'  尾部余量={fs - (c + total):,}' if ok else ''))

    if forced is not None:
        data = forced
    else:
        # 只在「hfs0_hdr 方案余量 < 全文件 1%」**且该处前 0x20 非全零**时信它，否则退回闭合反推
        # 2026-10-26 修正：スチームプリズン 的 hfs0_hdr 指到 0x171cb（前 0x20 全零 = 空区），
        # 而正确的 filesize-Σsizes = 0x1f022（前 0x20 非零、尾部余量 0）；旧逻辑只看余量比，选错 ⇒ NCA 全零。
        hdr_ok = any(buf[hdr_data:hdr_data + 0x20])
        if fs - (hdr_data + total) < max(0x1000, fs // 100) and hdr_ok:
            data = hdr_data
        else:
            if not hdr_ok:
                print('   ⚠ hfs0_hdr 起点前 0x20 全零（该处不是数据）⇒ 改用闭合反推 filesize-Σsizes')
            data = fs - total
            if fs - data > 0 and (fs - (data + total)) == 0 and fs - (hdr_data + total) > fs // 100:
                print('   ⚠ 闭合能对上但 secure 头部推不出来（可能夹了填充或伪 HFS0）'
                      '—— 结果可能错，请用 --at <hex> 或 scripts/nca_romfs.py 复核')

    print(f'\n选 @{off:#x}：{num} 个 NCA，Σsize={total:,}，数据起点 = {data:#x}')
    print(f'   起点前 20B = {buf[data:data + 0x20].hex(" ")}')

    cur = data
    for nm, sz in zip(names, sizes):
        print(f'   {nm:<44} @{cur:#x}  {sz:>14,}')
        cur += sz
    print(f'   末端 {cur:#x}  文件 {fs:#x}  差 {fs - cur:#x}')

    if outdir:
        os.makedirs(outdir, exist_ok=True)
        cur = data
        with open(path, 'rb') as f:
            for nm, sz in zip(names, sizes):
                if not nm.endswith('.nca'):
                    cur += sz
                    continue
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
                print(f'   导出 {nm} ({sz:,} B)')
                cur += sz
    return 0


if __name__ == '__main__':
    sys.exit(main())
