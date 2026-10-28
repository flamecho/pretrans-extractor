# -*- coding: utf-8 -*-
"""Angel Profile (PS2) Lua 5.0-variant chunk parser.

Layout (verified by consuming the file exactly):
  0x00  b'\\x1bLuaP' + 13 header bytes (fixed 18B)
  0x12  source string  (u32 len incl NUL + bytes)
        line u32 | nups,params,vararg,maxstack (4B) | u32 0 | u32 0
        nconst u32 | consts[]        const: t(1) [t=0 nil][t=1 bool+1B][t=3 float32][t=4 str(u32 len+bytes)]
        u32 0
        ncode u32 | code[ncode] u32
"""
import struct


class Chunk:
    def __init__(self, d):
        self.d = d
        self.consts = []
        self.code = []
        self.parse()

    def parse(self):
        d = self.d
        p = 0x12
        L = struct.unpack_from('<I', d, p)[0]
        self.source = d[p + 4:p + 4 + L]
        p += 4 + L
        self.line = struct.unpack_from('<I', d, p)[0]; p += 4
        # nups/params/vararg/maxstack
        self.maxstack = d[p + 3]; p += 4
        p += 12
        n = struct.unpack_from('<I', d, p)[0]; p += 4
        for _ in range(n):
            t = d[p]; p += 1
            if t == 0:
                self.consts.append(None)
            elif t == 1:
                self.consts.append(bool(d[p])); p += 1
            elif t == 3:
                self.consts.append(struct.unpack_from('<f', d, p)[0]); p += 4
            elif t == 4:
                L = struct.unpack_from('<I', d, p)[0]; p += 4
                self.consts.append(d[p:p + L - 1]); p += L
            else:
                raise ValueError('const type %d @%x' % (t, p - 1))
        p += 4
        nc = struct.unpack_from('<I', d, p)[0]; p += 4
        self.code = list(struct.unpack_from('<%dI' % nc, d, p))
        p += 4 * nc
        self.end = p


# Lua 5.0 opcode table
OP = ['MOVE', 'LOADK', 'LOADBOOL', 'LOADNIL', 'GETUPVAL', 'GETGLOBAL',
      'GETTABLE', 'SETGLOBAL', 'SETUPVAL', 'SETTABLE', 'NEWTABLE', 'SELF',
      'ADD', 'SUB', 'MUL', 'DIV', 'MOD', 'POW', 'UNM', 'NOT', 'LEN',
      'CONCAT', 'JMP', 'EQ', 'LT', 'LE', 'TEST', 'TESTSET', 'CALL',
      'TAILCALL', 'RETURN', 'FORLOOP', 'TFORPREP', 'TFORLOOP', 'SETLIST',
      'CLOSE', 'CLOSURE']


def dec(i):
    return OP[i & 0x3F], (i >> 6) & 0xFF, (i >> 14) & 0x1FF, (i >> 23) & 0x1FF


def bx(i):
    return (i >> 14) & 0x3FFFF


def s(x):
    return x.decode('cp932', 'replace') if isinstance(x, bytes) else x
