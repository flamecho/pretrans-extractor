# -*- coding: utf-8 -*-
"""SilentMoon FPK: u32 count, entries {u32 off, u32 size, char name[24]}, raw data."""
import io, os, struct, sys, collections


def read_fpk(path):
    b = open(path, 'rb').read()
    n = struct.unpack_from('<I', b, 0)[0]
    start = 4 + n * 32
    out = []
    for i in range(n):
        off, size = struct.unpack_from('<II', b, 4 + i * 32)
        name = b[4 + i * 32 + 8: 4 + i * 32 + 32].split(b'\0')[0].decode('cp932', 'replace')
        assert off >= start, (path, i, off, start)
        out.append((name, off, size))
    return b, out


def main():
    d = r'_work_silentmoon/iso'
    for fn in sorted(os.listdir(d)):
        if not fn.lower().endswith('.fpk'):
            continue
        b, ents = read_fpk(os.path.join(d, fn))
        names = [n for n, _, _ in ents]
        dup = len(names) - len(set(names))
        print('%-10s count=%5d dataStart=%9d minOff=%9d maxEnd=%9d dup=%d'
              % (fn, len(ents), 4 + len(ents) * 32,
                 min(o for _, o, _ in ents), max(o + s for _, o, s in ents), dup))
        print('   ext', dict(collections.Counter(os.path.splitext(n)[1].lower() for n in names)))
        print('   first', names[:3], 'last', names[-3:])


if __name__ == '__main__':
    main()
