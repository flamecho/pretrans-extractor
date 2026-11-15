# -*- coding: utf-8 -*-
"""列/取 NSP(XCI 内 PFS0) 的条目 —— 只读 PFS0 头，不涉及解密。

用法：
  python scripts/nsp_list.py <nsp>                 # 列条目
  python scripts/nsp_list.py <nsp> --get <子串> --out <文件>   # 按名字子串取一个文件
"""
import struct
import sys


def entries(path):
    with open(path, 'rb') as f:
        head = f.read(16)
        magic, count, strsz, _ = struct.unpack('<4sIII', head)
        if magic not in (b'PFS0', b'HFS0'):
            raise SystemExit('not PFS0: %r' % magic)
        ents = [struct.unpack('<IIII', f.read(16)) for _ in range(count)]
        strtab = f.read(strsz)
        base = 16 + 16 * count + strsz
    out = []
    for off, size, nameoff, _r in ents:
        end = strtab.index(b'\0', nameoff)
        out.append((strtab[nameoff:end].decode('utf-8', 'replace'), base + off, size))
    return out


def main():
    path = sys.argv[1]
    rows = entries(path)
    if '--get' in sys.argv:
        key = sys.argv[sys.argv.index('--get') + 1]
        dst = sys.argv[sys.argv.index('--out') + 1]
        hit = [r for r in rows if key in r[0]]
        if not hit:
            raise SystemExit('no entry matches %r' % key)
        name, off, size = hit[0]
        with open(path, 'rb') as f, open(dst, 'wb') as o:
            f.seek(off)
            left = size
            while left:
                b = f.read(min(8 << 20, left))
                if not b:
                    break
                o.write(b)
                left -= len(b)
        print('wrote %s (%d B) -> %s' % (name, size, dst))
        return
    for name, off, size in rows:
        print('%-40s %12d  @%#x' % (name, size, off))


if __name__ == '__main__':
    main()
