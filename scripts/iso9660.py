#!/usr/bin/env python3
"""iso9660.py —— 极简 ISO9660 列目录 / 抽取（无依赖，支持 PSP UMD 镜像）。

用法:
  python scripts/iso9660.py list  <iso> [子路径]
  python scripts/iso9660.py extract <iso> <outdir> [路径前缀 ...]
"""
import os
import struct
import sys

SEC = 2048


class ISO:
    def __init__(self, path):
        self.f = open(path, 'rb')
        vd = self.read_sector(16)
        if vd[1:6] != b'CD001':
            raise SystemExit('not ISO9660')
        self.root = self.parse_record(vd[156:156 + vd[156]])

    def read_sector(self, lba, count=1):
        self.f.seek(lba * SEC)
        return self.f.read(SEC * count)

    @staticmethod
    def parse_record(r):
        nlen = r[32]
        name = r[33:33 + nlen]
        return {
            'lba': struct.unpack_from('<I', r, 2)[0],
            'size': struct.unpack_from('<I', r, 10)[0],
            'flags': r[25],
            'name': name,
        }

    def entries(self, rec):
        data = self.read_sector(rec['lba'], (rec['size'] + SEC - 1) // SEC)[:rec['size']]
        i = 0
        out = []
        while i < len(data):
            ln = data[i]
            if ln == 0:
                i = (i // SEC + 1) * SEC
                continue
            if i + ln > len(data):
                break
            r = self.parse_record(data[i:i + ln])
            i += ln
            if r['name'] in (b'\x00', b'\x01'):
                continue
            r['name'] = r['name'].decode('latin1').split(';')[0]
            out.append(r)
        return out

    def walk(self, rec=None, prefix=''):
        rec = rec or self.root
        for e in self.entries(rec):
            p = prefix + e['name']
            if e['flags'] & 2:
                yield from self.walk(e, p + '/')
            else:
                yield p, e

    def find(self, path):
        path = path.strip('/').lower()
        for p, e in self.walk():
            if p.lower().strip('/') == path:
                return e
        return None

    def read_file(self, e):
        self.f.seek(e['lba'] * SEC)
        return self.f.read(e['size'])


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    cmd, iso_path = sys.argv[1], sys.argv[2]
    iso = ISO(iso_path)
    if cmd == 'list':
        sub = sys.argv[3].strip('/').lower() if len(sys.argv) > 3 else ''
        for p, e in iso.walk():
            if sub and not p.lower().startswith(sub):
                continue
            print('%12d  %s' % (e['size'], p))
    elif cmd == 'extract':
        outdir = sys.argv[3]
        prefixes = [p.strip('/').lower() for p in sys.argv[4:]]
        n = 0
        for p, e in iso.walk():
            low = p.lower()
            if prefixes and not any(low == x or low.startswith(x + '/') for x in prefixes):
                continue
            dst = os.path.join(outdir, p)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as w:
                w.write(iso.read_file(e))
            n += 1
            print('%12d  %s' % (e['size'], p))
        print('extracted', n)
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
