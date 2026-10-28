# -*- coding: utf-8 -*-
"""VSC VDP 容器解析（ラスト・エスコート2 ～深夜の甘い棘～ / PS2-JP）

VDP = "VSC_VDP_FILE"
  0x800 起 条目表，每条 0x34：
    name[16] + 16B 0 + u32 flags + u32 size + u32 x + u32 indexOff + u32 dataOff
  flags 低 16 位 = 条目数 / 高 16 位 = 类型

SCRIPT 条目：indexOff 处为索引（765 条 × 0x28；name@+0x10、off@+0x00（相对 dataOff）、size@+0x04）
             dataOff 处为数据区（每条 0x800 对齐）

用法：
  python scripts/vdp.py list DATA/SYSTEM.VDP
  python scripts/vdp.py x    DATA/SYSTEM.VDP SCRIPT outdir
"""
import os, sys, struct

def entries(path):
    f = open(path, 'rb'); f.seek(0x800); out = []
    while True:
        b = f.read(0x34)
        if len(b) < 0x34: break
        nm = b[:16].split(b'\x00')[0]
        if not all(0x20 <= c < 0x7f for c in nm) or not nm: break
        flags, size, x, ioff, doff = struct.unpack('<5I', b[32:52])
        out.append((nm.decode('cp932'), flags, size, x, ioff, doff))
    return out

def bundle(path, ioff, doff):
    """-> [(name, offset, size)]  数据区绝对偏移"""
    f = open(path, 'rb'); f.seek(ioff)
    out = []
    while True:
        b = f.read(0x28)
        if len(b) < 0x28: break
        nm = b[16:32].split(b'\x00')[0]
        if not nm or not all(0x20 <= c < 0x7f for c in nm): break
        off, size = struct.unpack('<2I', b[:8])
        out.append((nm.decode('cp932'), doff + off, size))
    return out

def main():
    cmd = sys.argv[1]
    path = sys.argv[2]
    if cmd == 'list':
        for nm, fl, size, x, ioff, doff in entries(path):
            print(f'{nm:14s} n={fl & 0xffff:5d} type={fl >> 16:2d} size={size:9d} idx={ioff:#010x} data={doff:#010x}')
    else:
        name, outdir = sys.argv[3], sys.argv[4]
        e = [x for x in entries(path) if x[0] == name][0]
        items = bundle(path, e[4], e[5])
        os.makedirs(outdir, exist_ok=True)
        f = open(path, 'rb'); bad = 0
        for nm, off, size in items:
            f.seek(off); b = f.read(size)
            open(os.path.join(outdir, nm), 'wb').write(b)
            if len(b) != size or (size >= 4 and struct.unpack('<I', b[:4])[0] != size): bad += 1
        print(f'{name}: {len(items)} 条 → {outdir}；头部 size 不符 {bad} 条')

if __name__ == '__main__':
    main()
