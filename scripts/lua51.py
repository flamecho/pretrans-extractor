# -*- coding: utf-8 -*-
"""Lua 5.1 bytecode 解析（Vita/PSV 乙女作常见：脚本编译为 luac 5.1）。"""

import struct


class Reader:
    def __init__(self, data):
        self.d = data
        self.p = 0

    def byte(self):
        v = self.d[self.p]
        self.p += 1
        return v

    def int32(self):
        v = struct.unpack_from('<i', self.d, self.p)[0]
        self.p += 4
        return v

    def uint32(self):
        v = struct.unpack_from('<I', self.d, self.p)[0]
        self.p += 4
        return v

    def u64(self):
        v = struct.unpack_from('<Q', self.d, self.p)[0]
        self.p += 8
        return v

    def number(self):
        v = struct.unpack_from('<d', self.d, self.p)[0]
        self.p += 8
        return v

    def string(self):
        n = self.uint32()
        if n == 0:
            return None
        raw = self.d[self.p:self.p + n - 1]
        self.p += n
        return raw

    def bytes(self, n):
        raw = self.d[self.p:self.p + n]
        self.p += n
        return raw


class Proto:
    __slots__ = ('source', 'line', 'lastline', 'nups', 'numparams', 'vararg',
                 'maxstack', 'code', 'consts', 'protos', 'upnames')

    def __init__(self):
        self.consts = []
        self.protos = []


def read_proto(r):
    pr = Proto()
    pr.source = r.string()
    pr.line = r.int32()
    pr.lastline = r.int32()
    pr.nups = r.byte()
    pr.numparams = r.byte()
    pr.vararg = r.byte()
    pr.maxstack = r.byte()
    n = r.int32()
    pr.code = list(struct.unpack_from('<%dI' % n, r.d, r.p))
    r.p += 4 * n
    n = r.int32()
    for _ in range(n):
        t = r.byte()
        if t == 0:
            pr.consts.append(None)
        elif t == 1:
            pr.consts.append(r.byte())
        elif t == 3:
            pr.consts.append(r.number())
        elif t == 4:
            pr.consts.append(r.string())
        else:
            raise ValueError('bad const type %d at %d' % (t, r.p))
    n = r.int32()
    for _ in range(n):
        pr.protos.append(read_proto(r))
    n = r.int32()
    pr.upnames = [r.string() for _ in range(n)]
    return pr


def parse(data):
    r = Reader(data)
    assert data[:4] == b'\x1bLua', data[:4]
    ver = r.byte()
    r.byte()
    r.byte()  # endian
    r.byte(); r.byte(); r.byte(); r.byte()
    r.number()  # lua_Number size check byte
    r.byte()
    main = read_proto(r)
    return main


def walk(pr, out, path='main'):
    out.append((path, pr))
    for i, sub in enumerate(pr.protos):
        walk(sub, out, '%s.%d' % (path, i))
    return out


# ---- Lua 5.1 opcode table ----
OPNAMES = ['MOVE', 'LOADK', 'LOADBOOL', 'LOADNIL', 'GETUPVAL', 'GETGLOBAL',
           'GETTABLE', 'SETGLOBAL', 'SETUPVAL', 'SETTABLE', 'NEWTABLE', 'SELF',
           'ADD', 'SUB', 'MUL', 'DIV', 'MOD', 'POW', 'UNM', 'NOT', 'LEN',
           'CONCAT', 'JMP', 'EQ', 'LT', 'LE', 'TEST', 'TESTSET', 'CALL',
           'TAILCALL', 'RETURN', 'FORLOOP', 'FORPREP', 'TFORLOOP', 'SETLIST',
           'CLOSE', 'CLOSURE', 'VARARG']


def decode(i):
    op = i & 0x3F
    a = (i >> 6) & 0xFF
    c = (i >> 14) & 0x1FF
    b = (i >> 23) & 0x1FF
    bx = (i >> 14) & 0x3FFFF
    sbx = bx - 131071
    return OPNAMES[op], a, b, c, bx, sbx
