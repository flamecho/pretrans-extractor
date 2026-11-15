# -*- coding: utf-8 -*-
"""Utage .book 解析（格式依据 storycraft/unity-utage-book 的 reader.rs）。

header: 7×u32 + name(str) + import_version(u32)
sheet : rows_len(u32) + rows + name(str) + sheet_type + text_length + header_row + 8B pad
row   : index(u32) + strings_len(u32) + strings + empty(u32) + comment_out(u32)
str   : len(u32) + bytes + pad4
"""
import struct


class R:
    def __init__(self, b):
        self.b = b
        self.p = 0

    def u32(self):
        v = struct.unpack_from('<I', self.b, self.p)[0]
        self.p += 4
        return v

    def s(self):
        n = self.u32()
        v = self.b[self.p:self.p + n].decode('utf-8', 'replace')
        self.p += n
        if n % 4:
            self.p += 4 - n % 4
        return v

    def eof(self):
        return self.p >= len(self.b)


def parse_book(raw):
    r = R(raw)
    hdr = [r.u32() for _ in range(7)]
    name = r.s()
    ver = r.u32()
    nsheet = r.u32()
    sheets = []
    for _ in range(nsheet):
        nrows = r.u32()
        rows = []
        for _ in range(nrows):
            idx = r.u32()
            n = r.u32()
            cells = [r.s() for _ in range(n)]
            empty = r.u32()
            comment = r.u32()
            rows.append({'index': idx, 'cells': cells, 'empty': empty, 'comment': comment})
        sname = r.s()
        stype = r.u32()
        tlen = r.u32()
        hrow = r.u32()
        r.p += 8
        sheets.append({'name': sname, 'type': stype, 'text_length': tlen,
                       'header_row': hrow, 'rows': rows})
    return {'name': name, 'ver': ver, 'sheets': sheets, 'end': r.p, 'len': len(raw)}
