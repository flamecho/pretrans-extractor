#!/usr/bin/env python3
"""カヌチ 二つの翼 (PSP / Idea Factory 'YDP1') 解包
结构:
  [0x00] 'YDP1'
  [0x04] u32 filesize
  [0x08] u32 (?)
  [0x0C] u32 组表字节数 (= 组数*0x20)
  [0x10] u32 数据区起点 (也是全局文件目录末尾)
  [0x14] u32 (?)
  组表 @0x20, 每条 0x20: name[16] stored u32 orig u32 flag u16 count u16 grp_off u32
  全局文件目录 @0x20+tblsize, 每条 0x28: name[16] a u32 b u32 c u32 size u32 size2 u32 rel_off u32
  数据区 @0x10; 组数据起点 = 0x10 + grp_off; 文件 = 组起点 + rel_off
"""
import os, struct, sys


def parse(path):
    d = open(path, 'rb').read()
    assert d[:4] == b'YDP1', d[:4]
    fsize, h8, tblsize, data0 = struct.unpack('<IIII', d[4:20])
    n = tblsize // 0x20
    groups = []
    for i in range(n):
        e = d[0x20 + i * 0x20: 0x40 + i * 0x20]
        name = e[:16].split(b'\0')[0].decode('latin1')
        a, b = struct.unpack('<II', e[16:24])
        fl, cnt = struct.unpack('<HH', e[24:28])
        off = struct.unpack('<I', e[28:32])[0]
        groups.append(dict(name=name, stored=a, orig=b, cnt=cnt, off=off,
                           base=data0 + off))
    def okname(q, d=d):
        nm = d[q:q + 16].rstrip(b'\0')
        return nm and all(32 <= c < 127 for c in nm)
    dstart = None
    for q in range(0x20 + tblsize, 0x20 + tblsize + 0x800):
        if okname(q) and okname(q + 0x28) and okname(q + 0x50):
            dstart = q
            break
    files = []
    p = dstart
    while p < data0:
        e = d[p:p + 0x28]
        nm = e[:16].rstrip(b'\0')
        if not nm or not all(32 <= c < 127 for c in nm):
            break
        f = struct.unpack('<6I', e[16:40])
        files.append(dict(name=nm.decode('latin1'), size=f[3], size2=f[4], off=f[5]))
        p += 0x28
    # 组归属: 归到「base <= abs < base+stored」的组
    for f in files:
        f['abs'] = None
    gi = 0
    prev = -1
    for f in files:
        if f['off'] < prev:          # 偏移归零 => 进入下一组
            gi += 1
        while gi < len(groups) - 1 and f['off'] >= groups[gi]['stored']:
            gi += 1
        g = groups[gi]
        f['group'] = g['name']
        f['abs'] = g['base'] + f['off']
        prev = f['off']
    return d, groups, files, data0


def main():
    path, outdir = sys.argv[1], sys.argv[2]
    only = sys.argv[3] if len(sys.argv) > 3 else None
    d, groups, files, data0 = parse(path)
    print('groups %d files %d data0 %06x' % (len(groups), len(files), data0))
    man = []
    for f in files:
        if only and f['group'] != only:
            continue
        sub = os.path.join(outdir, f['group'])
        os.makedirs(sub, exist_ok=True)
        blob = d[f['abs']:f['abs'] + f['size']]
        if len(blob) != f['size']:
            print('TRUNC', f['name'])
        open(os.path.join(sub, f['name']), 'wb').write(blob)
        man.append((f['group'], f['name'], f['size'], f['abs']))
    print('wrote', len(man))
    with open(os.path.join(outdir, '_manifest.txt'), 'w', encoding='utf-8') as w:
        for r in man:
            w.write('%s\t%s\t%d\t%x\n' % r)


if __name__ == '__main__':
    main()
