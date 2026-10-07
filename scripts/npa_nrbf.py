import struct

PRIM_SIZE = {1:1, 2:1, 3:2, 5:16, 6:8, 7:2, 8:4, 9:8, 10:1, 11:4, 12:8, 13:8, 14:2, 15:4, 16:8}


class Ref:
    __slots__ = ('oid',)
    def __init__(self, oid):
        self.oid = oid
    def __repr__(self):
        return 'Ref(%d)' % self.oid


class ClassObj:
    __slots__ = ('oid', 'name', 'members')
    def __init__(self, oid, name):
        self.oid = oid
        self.name = name
        self.members = {}


class Parser:
    def __init__(self, buf):
        self.b = buf
        self.p = 0
        self.objs = {}
        self.classes = {}   # oid -> (name, member_names)
        self.refs = {}

    def u8(self):
        v = self.b[self.p]; self.p += 1; return v

    def i32(self):
        v = struct.unpack_from('<i', self.b, self.p)[0]; self.p += 4; return v

    def u32(self):
        v = struct.unpack_from('<I', self.b, self.p)[0]; self.p += 4; return v

    def raw(self, n):
        v = self.b[self.p:self.p + n]; self.p += n; return v

    def lpstr(self):
        n = 0; shift = 0
        while True:
            c = self.u8()
            n |= (c & 0x7f) << shift
            if not (c & 0x80):
                break
            shift += 7
        return self.raw(n).decode('utf-8', 'replace')

    def prim(self, pt):
        if pt == 1:
            return self.u8() != 0
        if pt == 2:
            return self.u8()
        if pt == 10:
            v = struct.unpack_from('<b', self.b, self.p)[0]; self.p += 1; return v
        if pt == 3:
            v = struct.unpack_from('<H', self.b, self.p)[0]; self.p += 2; return chr(v)
        if pt == 7:
            v = struct.unpack_from('<h', self.b, self.p)[0]; self.p += 2; return v
        if pt == 14:
            v = struct.unpack_from('<H', self.b, self.p)[0]; self.p += 2; return v
        if pt == 8:
            return self.i32()
        if pt == 15:
            return self.u32()
        if pt == 9:
            v = struct.unpack_from('<q', self.b, self.p)[0]; self.p += 8; return v
        if pt == 16:
            v = struct.unpack_from('<Q', self.b, self.p)[0]; self.p += 8; return v
        if pt == 11:
            v = struct.unpack_from('<f', self.b, self.p)[0]; self.p += 4; return v
        if pt == 6:
            v = struct.unpack_from('<d', self.b, self.p)[0]; self.p += 8; return v
        if pt in (12, 13):
            return self.raw(8)
        if pt == 5:
            return self.raw(16)
        raise ValueError('prim %d @%d' % (pt, self.p))

    def read_classinfo(self, oid):
        name = self.lpstr()
        cnt = self.i32()
        members = [self.lpstr() for _ in range(cnt)]
        return (oid, name, members)

    def read_membertypeinfo(self, cnt):
        bts = [self.u8() for _ in range(cnt)]
        info = []
        for bt in bts:
            d = {'bt': bt}
            if bt in (0, 7):
                d['pt'] = self.u8()
            elif bt == 3:
                d['name'] = self.lpstr()
            elif bt == 4:
                d['name'] = self.lpstr()
                d['lib'] = self.i32()
            info.append(d)
        return info

    def read_value(self, t):
        bt = t['bt']
        if bt == 0:
            return self.prim(t['pt'])
        if bt in (1, 2, 3, 4, 5, 6, 7):
            return self.read_record()
        raise ValueError('bt %d' % bt)

    def read_members(self, member_names, mti):
        vals = {}
        for nm, t in zip(member_names, mti):
            vals[nm] = self.read_value(t)
        return vals

    def read_record(self):
        rt = self.u8()
        if rt == 0:  # header
            self.i32(); self.i32(); self.i32(); self.i32()
            return ('header',)
        if rt == 1:  # ClassWithId
            oid = self.i32(); mid = self.i32()
            nm, members, mti = self.classes[mid]
            obj = ClassObj(oid, nm)
            self.objs[oid] = obj
            self.classes[oid] = (nm, members, mti)
            obj.members = self.read_members(members, mti)
            return obj
        if rt in (2, 3, 4, 5):
            oid = self.i32()
            _, nm, members = self.read_classinfo(oid)
            if rt in (2, 3):
                mti = [{'bt': 2} for _ in members]
            else:
                mti = self.read_membertypeinfo(len(members))
            if rt in (3, 5):
                self.i32()  # library id
            self.classes[oid] = (nm, members, mti)
            obj = ClassObj(oid, nm)
            self.objs[oid] = obj
            obj.members = self.read_members(members, mti)
            return obj
        if rt == 6:  # BinaryObjectString
            oid = self.i32()
            s = self.lpstr()
            self.objs[oid] = s
            return s
        if rt == 7:  # BinaryArray
            oid = self.i32()
            atype = self.u8(); rank = self.i32()
            lengths = [self.i32() for _ in range(rank)]
            if atype == 3:
                self.i32()                       # single offset
            elif atype in (4, 5):
                [self.i32() for _ in range(rank)]  # jagged/rectangular offsets
            bt = self.u8()
            d = {'bt': bt}
            if bt in (0, 7):
                d['pt'] = self.u8()
            elif bt == 3:
                d['name'] = self.lpstr()
            elif bt == 4:
                d['name'] = self.lpstr(); d['lib'] = self.i32()
            n = lengths[0] if lengths else 0
            arr = [self.read_value(d) for _ in range(n)]
            self.objs[oid] = arr
            return arr
        if rt == 8:  # MemberPrimitiveTyped
            pt = self.u8()
            return self.prim(pt)
        if rt == 9:  # MemberReference
            oid = self.i32()
            r = Ref(oid)
            self.refs[oid] = r
            return r
        if rt == 10:
            return None
        if rt == 11:
            return ('end',)
        if rt == 12:  # BinaryLibrary
            self.i32()
            return ('lib', self.lpstr())
        if rt == 13:
            return [None] * self.u8()
        if rt == 14:
            return [None] * self.i32()
        if rt == 15:  # ArraySinglePrimitive
            oid = self.i32(); n = self.i32(); pt = self.u8()
            arr = [self.prim(pt) for _ in range(n)]
            self.objs[oid] = arr
            return arr
        if rt == 16:  # ArraySingleObject
            oid = self.i32(); n = self.i32()
            arr = [self.read_record() for _ in range(n)]
            self.objs[oid] = arr
            return arr
        if rt == 17:  # ArraySingleString
            oid = self.i32(); n = self.i32()
            arr = [self.read_record() for _ in range(n)]
            self.objs[oid] = arr
            return arr
        raise ValueError('record %d @%d' % (rt, self.p - 1))

    def parse(self):
        self.read_record()  # header
        while self.p < len(self.b):
            try:
                r = self.read_record()
            except Exception as e:
                break
            if isinstance(r, tuple) and r and r[0] == 'end':
                break
        return self.objs, self.classes


def load(path):
    import zlib
    d = open(path, 'rb').read()
    assert d[:8] == b'GARbroDB'
    raw = zlib.decompress(d[12:])
    p = Parser(raw)
    return p.parse()
