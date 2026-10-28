# -*- coding: utf-8 -*-
"""Lua 5.3 luac 解析（PSV 变体：32 位、lua_Number=float32、varint 长度）。

头：1b 4c 75 61 53 00 <LUAC_DATA 6B> <sizes 5B> <LUAC_INT 4B> <LUAC_NUM 4B>
字符串长度/计数用 7bit varint（低字节先）。
"""

import struct


class R:
    __slots__ = ('d', 'p')

    def __init__(self, d):
        self.d = d
        self.p = 0

    def u8(self):
        v = self.d[self.p]
        self.p += 1
        return v

    def var(self):
        """Lua 5.3 LoadVar：7bit/字节，最高位继续。"""
        x = 0
        shift = 0
        while True:
            b = self.d[self.p]
            self.p += 1
            x |= (b & 0x7F) << shift
            if b < 0x80:
                return x
            shift += 7

    def bytes(self, n):
        v = self.d[self.p:self.p + n]
        self.p += n
        return v

    def i32(self):
        v = struct.unpack_from('<i', self.d, self.p)[0]
        self.p += 4
        return v

    def u32(self):
        v = struct.unpack_from('<I', self.d, self.p)[0]
        self.p += 4
        return v

    def f32(self):
        v = struct.unpack_from('<f', self.d, self.p)[0]
        self.p += 4
        return v


class Proto:
    __slots__ = ('source', 'line', 'lastline', 'numparams', 'vararg', 'maxstack',
                 'code', 'consts', 'upvals', 'protos', 'lineinfo', 'locvars',
                 'upnames')

    def __repr__(self):
        return '<Proto %r %d-%d>' % (self.source, self.line, self.lastline)


def load_string(r):
    n = r.var()
    if n == 0:
        return None
    raw = r.bytes(n)
    return raw[:-1] if raw.endswith(b'\x00') else raw


def read_proto(r):
    pr = Proto()
    pr.source = load_string(r)
    pr.line = r.var()
    pr.lastline = r.var()
    pr.numparams = r.u8()
    pr.vararg = r.u8()
    pr.maxstack = r.u8()
    n = r.var()
    pr.code = list(struct.unpack_from('<%dI' % n, r.d, r.p))
    r.p += 4 * n
    n = r.var()
    pr.consts = []
    for _ in range(n):
        t = r.u8()
        if t == 0:
            pr.consts.append(None)
        elif t == 1:
            pr.consts.append(bool(r.u8()))
        elif t == 3:
            pr.consts.append(r.f32())
        elif t == 19:
            pr.consts.append(r.i32())
        elif t == 4 or t == 20:
            pr.consts.append(load_string(r))
        else:
            raise ValueError('const type %d @%d' % (t, r.p))
    n = r.var()
    pr.upvals = [r.u8() for _ in range(2 * n)]
    n = r.var()
    pr.protos = [read_proto(r) for _ in range(n)]
    n = r.var()
    pr.lineinfo = list(struct.unpack_from('<%di' % n, r.d, r.p))
    r.p += 4 * n
    n = r.var()
    pr.locvars = []
    for _ in range(n):
        name = load_string(r)
        pr.locvars.append((name, r.var(), r.var()))
    n = r.var()
    pr.upnames = [load_string(r) for _ in range(n)]
    return pr


def parse(data):
    r = R(data)
    assert data[:4] == b'\x1bLua', data[:4]
    # 头部长度随编译器变体浮动（本作 26B）：以主 chunk 的源文件名锚定
    i = data.find(b'@C:')
    if i < 0:
        i = data.find(b'@')
    start = i - 1
    while start > 4 and data[start] >= 0x80:
        start -= 1
    r.p = start
    return read_proto(r)


def walk(pr, out=None, path='main'):
    if out is None:
        out = []
    out.append((path, pr))
    for i, sub in enumerate(pr.protos):
        walk(sub, out, '%s.%d' % (path, i))
    return out


OPS = ['MOVE', 'LOADI', 'LOADF', 'LOADK', 'LOADKX', 'LOADBOOL', 'LOADNIL',
       'GETUPVAL', 'GETTABUP', 'GETTABLE', 'SETTABUP', 'SETUPVAL', 'SETTABLE',
       'NEWTABLE', 'SELF', 'ADD', 'SUB', 'MUL', 'MOD', 'POW', 'DIV', 'IDIV',
       'BAND', 'BOR', 'BXOR', 'SHL', 'SHR', 'UNM', 'BNOT', 'NOT', 'LEN',
       'CONCAT', 'JMP', 'EQ', 'LT', 'LE', 'TEST', 'TESTSET', 'CALL',
       'TAILCALL', 'RETURN', 'FORLOOP', 'FORPREP', 'TFORCALL', 'TFORLOOP',
       'SETLIST', 'CLOSURE', 'VARARG', 'EXTRAARG']


def decode(word):
    op = word & 0x7F
    a = (word >> 7) & 0xFF
    c = (word >> 15) & 0x1FF
    b = (word >> 24) & 0x1FF
    bx = (word >> 15) & 0x3FFFF
    sbx = bx - 131071
    ax = (word >> 7) & 0x1FFFFFF
    return OPS[op] if op < len(OPS) else 'OP%d' % op, a, b, c, bx, sbx, ax


def disasm(pr):
    out = []
    for i, w in enumerate(pr.code):
        op, a, b, c, bx, sbx, ax = decode(w)
        extra = ''
        if op in ('LOADK', 'CLOSURE'):
            extra = ' K[%d]=%r' % (bx, pr.consts[bx] if bx < len(pr.consts) else '?')
        elif op == 'LOADI':
            extra = ' %d' % sbx
        elif op == 'LOADF':
            extra = ' %d' % sbx
        elif op in ('GETTABUP', 'GETTABLE'):
            extra = ' K[%d]=%r' % (c, pr.consts[c] if c < len(pr.consts) else '?')
        elif op == 'SETTABUP':
            extra = ' K[%d]=%r' % (b, pr.consts[b] if b < len(pr.consts) else '?')
        elif op in ('CALL',):
            extra = ' nargs=%s nres=%s' % (b - 1 if b else 'var', c - 1 if c else 'var')
        out.append('%4d %-9s A=%-3d B=%-3d C=%-3d %s' % (i, op, a, b, c, extra))
    return out
