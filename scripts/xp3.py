#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""蝶の毒 華の鎖 XP3 索引列挙 + ファイル抽出 (KiriKiri XP3)"""
import struct, zlib, sys, os, io, json

class XP3:
    def __init__(self, path):
        self.path = path
        self.data = open(path, 'rb').read()
        self.files = {}   # name -> list[(off,size,is_compressed,orig_size)]
        self._parse()

    def _find_index(self):
        d = self.data
        # 优先：header 0x20 处 u64
        cands = []
        v = struct.unpack_from('<Q', d, 0x20)[0]
        if 0 < v < len(d):
            cands.append(v)
        # 兜底：尾部扫描
        start = max(0, len(d) - 2_000_000)
        i = start
        while i < len(d) - 2:
            if d[i] == 0x78 and d[i+1] in (0x01, 0x5e, 0x9c, 0xda):
                cands.append(i)
            i += 1
        for c in cands:
            for k in range(0, 64):
                p = c + k
                if p >= len(d):
                    break
                if d[p] == 0x78 and d[p+1] in (0x01, 0x5e, 0x9c, 0xda):
                    try:
                        out = zlib.decompressobj().decompress(d[p:])
                        if out[:4] == b'File':
                            return out
                    except Exception:
                        pass
        raise RuntimeError('index not found')

    def _parse(self):
        out = self._find_index()
        p = 0
        while p + 12 <= len(out):
            tag = out[p:p+4]
            size = struct.unpack_from('<Q', out, p+4)[0]
            if tag != b'File':
                break
            payload = out[p+12:p+12+size]
            name, segs = self._parse_file(payload)
            if name is not None:
                self.files[name] = segs
            p += 12 + size
        return len(out)

    @staticmethod
    def _parse_file(payload):
        q, name, segs = 0, None, []
        while q + 12 <= len(payload):
            tag = payload[q:q+4]
            size = struct.unpack_from('<Q', payload, q+4)[0]
            sp = payload[q+12:q+12+size]
            if tag == b'info':
                nlen = struct.unpack_from('<H', sp, 20)[0]
                name = sp[22:22+nlen*2].decode('utf-16-le', 'replace')
            elif tag == b'segm':
                for i in range(0, len(sp)-27, 28):
                    _, off, a, b = struct.unpack_from('<IQQQ', sp, i)
                    # a = disk size(compressed), b = original size
                    segs.append((off, a, b))
            q += 12 + size
        return name, segs

    def read(self, name):
        buf = bytearray()
        for off, comp, orig in self.files[name]:
            raw = self.data[off:off+comp]
            if comp == 0:
                continue
            if comp == orig:
                buf += raw
            else:
                try:
                    buf += zlib.decompress(raw)
                except Exception:
                    buf += raw
        return bytes(buf)

if __name__ == '__main__':
    x = XP3(sys.argv[1])
    print('files=%d' % len(x.files))
    exts = {}
    for n in x.files:
        e = os.path.splitext(n)[1].lower()
        exts[e] = exts.get(e, 0) + 1
    for e, c in sorted(exts.items(), key=lambda kv: -kv[1]):
        print('  %-12s %d' % (e or '(none)', c))
    if len(sys.argv) > 2 and sys.argv[2] == 'list':
        for n in sorted(x.files):
            print(n)
