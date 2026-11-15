#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""RAR5 文件头遍历器：不解压、只读块头，快速列出文件名（大固实包用）。

用法: python rar5_list.py <archive.rar> [最多列几个]
"""
import io
import sys


def vint(b, p):
    """读 RAR5 variable-length int（7 bit/byte，LSB first）。返回 (值, 新偏移)。"""
    v = 0
    shift = 0
    while True:
        if p >= len(b):
            raise EOFError
        c = b[p]
        p += 1
        v |= (c & 0x7F) << shift
        shift += 7
        if not (c & 0x80):
            return v, p


def main():
    path = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    f = io.open(path, 'rb')
    sig = f.read(8)
    if sig != b'Rar!\x1a\x07\x01\x00':
        print('不是 RAR5')
        return 2
    pos = 8
    total = 0
    shown = 0
    while True:
        f.seek(pos)
        head = f.read(64 * 1024)
        if len(head) < 12:
            break
        p = 0
        crc = int.from_bytes(head[0:4], 'little')
        p = 4
        try:
            hsize, p = vint(head, p)
        except EOFError:
            break
        if hsize <= 0 or hsize > 2 * 1024 * 1024:
            print('块大小异常 @%d: %d' % (pos, hsize))
            break
        body = head[p:p + hsize]
        if len(body) < hsize:
            f.seek(pos + 4)
            body = f.read(hsize)
        q = 0
        htype, q = vint(body, q)
        hflags, q = vint(body, q)
        extrasize = 0
        datasize = 0
        if hflags & 0x0001:
            extrasize, q = vint(body, q)
        if hflags & 0x0002:
            datasize, q = vint(body, q)
        if htype == 2:      # file header
            fflags, q = vint(body, q)
            unpsize, q = vint(body, q)
            attr, q = vint(body, q)
            if fflags & 0x0002:
                q += 4
            if fflags & 0x0004:
                q += 4
            comp, q = vint(body, q)
            host, q = vint(body, q)
            nlen, q = vint(body, q)
            name = body[q:q + nlen]
            try:
                nm = name.decode('utf-8')
            except UnicodeDecodeError:
                nm = name.decode('cp932', 'replace')
            total += 1
            if shown < limit:
                print('%12d  %s' % (unpsize, nm))
                shown += 1
            pos += 4 + hsize + datasize
        elif htype == 5:    # end of archive
            break
        elif htype == 4:
            print('!!! 加密头')
            break
        else:
            pos += 4 + hsize + datasize
        if total > 20000:
            break
    print('--- 文件数 %d（%s）' % (total, '已列完' if total <= limit else '仅列前 %d' % limit))
    f.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
