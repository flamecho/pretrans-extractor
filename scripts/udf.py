#!/usr/bin/env python3
"""极简 UDF 只读解析（PS2 桥接盘用）：列目录 / 抽取文件。"""
import os
import struct
import sys

SEC = 2048


class UDF:
    def __init__(self, path):
        self.f = open(path, 'rb')
        self.size = os.path.getsize(path)
        self.nsec = self.size // SEC
        self.part_start = 0
        self.part_len = 0
        self._find_anchor()

    def sec(self, n, count=1):
        self.f.seek(n * SEC)
        return self.f.read(SEC * count)

    @staticmethod
    def tag(b, off=0):
        tid, ver, ck, res, serial, crc, crclen, loc = struct.unpack_from('<HHBBHHHI', b, off)
        return {'id': tid, 'loc': loc}

    def _find_anchor(self):
        for s in (256, self.nsec - 256, self.nsec - 1):
            if s < 0:
                continue
            b = self.sec(s)
            if self.tag(b)['id'] == 2:
                ln, loc = struct.unpack_from('<II', b, 16)
                self._read_vds(loc, ln)
                return
        raise SystemExit('AVDP not found')

    def _read_vds(self, loc, ln):
        data = self.sec(loc, (ln + SEC - 1) // SEC)[:ln]
        pd = None
        for off in range(0, len(data), SEC):
            t = self.tag(data, off)
            if t['id'] == 5:
                pd = data[off:off + SEC]
            elif t['id'] == 6:
                self.lvd = data[off:off + SEC]
            elif t['id'] == 8:
                break
        if pd is None:
            raise SystemExit('no PD')
        self.part_start = struct.unpack_from('<I', pd, 188)[0]
        self.part_len = struct.unpack_from('<I', pd, 192)[0]
        self.fsd_loc = struct.unpack_from('<I', self.lvd, 248 + 4)[0]

    def blk(self, lb, length=SEC):
        n = (length + SEC - 1) // SEC
        self.f.seek((self.part_start + lb) * SEC)
        return self.f.read(n * SEC)[:length]

    def read_icb(self, lb):
        """返回 (is_dir, data, info_len)"""
        b = self.blk(lb)
        t = self.tag(b)
        if t['id'] == 261:
            info_len = struct.unpack_from('<Q', b, 56)[0]
            l_ea = struct.unpack_from('<I', b, 168)[0]
            l_ad = struct.unpack_from('<I', b, 172)[0]
            base = 176
        elif t['id'] == 266:
            info_len = struct.unpack_from('<Q', b, 56)[0]
            l_ea = struct.unpack_from('<I', b, 208)[0]
            l_ad = struct.unpack_from('<I', b, 212)[0]
            base = 216
        elif t['id'] == 259:  # indirect entry
            return self.read_icb(struct.unpack_from('<I', b, 20)[0])
        else:
            return None, b'', 0
        ftype = b[16 + 11] & 7
        adtype = struct.unpack_from('<H', b, 34)[0] & 7
        ads = b[base + l_ea: base + l_ea + l_ad]
        segs = []
        if adtype == 3:
            data = ads
            return (ftype == 1), data, info_len
        step = 8 if adtype == 0 else 16
        i = 0
        while i + step <= len(ads):
            alen = struct.unpack_from('<I', ads, i)[0]
            if alen == 0:
                break
            segs.append((struct.unpack_from('<I', ads, i + 4)[0], alen & 0x3FFFFFFF))
            i += step
        data = b''.join(self.blk(seg[0], seg[1]) for seg in segs)
        if info_len and len(data) > info_len:
            data = data[:info_len]
        return (ftype == 1), data, info_len

    def list_dir(self, lb):
        isdir, data, _ = self.read_icb(lb)
        out = []
        off = 0
        while off + 38 <= len(data):
            t = self.tag(data, off)
            if t['id'] != 257:
                break
            chars = data[off + 18]
            lfi = data[off + 19]
            icb_len, icb_loc = struct.unpack_from('<II', data, off + 20)
            lui = struct.unpack_from('<H', data, off + 36)[0]
            nameb = data[off + 38 + lui: off + 38 + lui + lfi]
            off = (off + 38 + lui + lfi + 3) & ~3
            if chars & 0x0C:
                continue
            name = nameb.decode('utf-16-be', 'replace') if nameb else '.'
            out.append((name, bool(chars & 0x02), icb_loc))
        return out

    def walk(self, lb=None, prefix='', depth=0):
        if lb is None:
            lb = self.fsd_loc
            fsd = self.blk(lb, 4096)
            lb = struct.unpack_from('<I', fsd, 404)[0]
        if depth > 6:
            return
        for name, isdir, icb_loc in self.list_dir(lb):
            p = prefix + '/' + name
            yield p, isdir, icb_loc
            if isdir:
                yield from self.walk(icb_loc, p, depth + 1)

    def read_file(self, lb):
        isdir, data, info = self.read_icb(lb)
        return data


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    cmd, iso = sys.argv[1], sys.argv[2]
    u = UDF(iso)
    if cmd == 'list':
        n = 0
        for p, isdir, loc in u.walk():
            print(('D' if isdir else 'F'), loc, p)
            n += 1
            if n > 8000:
                print('...truncated')
                break
    elif cmd == 'extract':
        outdir = sys.argv[3]
        want = sys.argv[4].lower() if len(sys.argv) > 4 else ''
        for p, isdir, loc in u.walk():
            if isdir or (want and want not in p.lower()):
                continue
            data = u.read_file(loc)
            dst = os.path.join(outdir, p.lstrip('/'))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as w:
                w.write(data)
            print(len(data), p)


if __name__ == '__main__':
    main()
