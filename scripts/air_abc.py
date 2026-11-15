"""Adobe AIR / SWF 的 ABC(ActionScript 3 字节码) 解析器 + 反汇编器。

用途：读 SWF 里 `jp.co.woga.util:PackageLoader` 这类类，看清它怎么读 / 解
`package.dat`、`system.dat`。

用法：
    python scripts/air_abc.py <swf>                       # 概览
    python scripts/air_abc.py <swf> --str <关键字>         # 搜常量池字符串
    python scripts/air_abc.py <swf> --class <关键字>       # 反汇编匹配到的类
    python scripts/air_abc.py <swf> --method <方法号>       # 反汇编单个方法体
"""
import struct
import sys
import zlib


# ---------------- SWF 容器 ----------------
def load_swf(path):
    d = open(path, 'rb').read()
    sig = d[:3]
    if sig == b'CWS':
        body = zlib.decompress(d[8:])
    elif sig == b'FWS':
        body = d[8:]
    elif sig == b'ZWS':
        import lzma
        body = lzma.decompress(d[12:], format=lzma.FORMAT_ALONE)
    else:
        raise SystemExit('not a swf: %r' % sig)
    return b'FWS' + d[3:8] + body          # 完整 SWF（含 8 字节头）


def u8(b, p):
    return b[p], p + 1


def u16(b, p):
    return struct.unpack_from('<H', b, p)[0], p + 2


def u32(b, p):
    return struct.unpack_from('<I', b, p)[0], p + 4


def u30(b, p):
    r = 0
    for i in range(5):
        c = b[p]
        p += 1
        r |= (c & 0x7F) << (7 * i)
        if not c & 0x80:
            return r, p
    raise ValueError('bad u30 at %d' % p)


def s32v(b, p):
    r = 0
    for i in range(5):
        c = b[p]
        p += 1
        r |= (c & 0x7F) << (7 * i)
        if not c & 0x80:
            if c & 0x40:
                r -= 1 << (7 * (i + 1))
            return r, p
    raise ValueError('bad s32 at %d' % p)


def swf_tags(body):
    p = 8
    nbits = body[p] >> 3
    p += (5 + 4 * nbits + 7) // 8
    p += 4
    out = []
    while p + 2 <= len(body):
        cl, p = u16(body, p)
        code, ln = cl >> 6, cl & 0x3F
        if ln == 0x3F:
            ln, p = u32(body, p)
        out.append((code, body[p:p + ln]))
        p += ln
        if code == 0:
            break
    return out


# ---------------- ABC ----------------
class ABC:
    def __init__(self, data):
        self.d = data
        self.ints, self.uints, self.dbls, self.strs = [], [], [], []
        self.nss, self.ns_sets, self.mnames = [], [], []
        self.methods = []       # [param_count, ret, name, flags]
        self.instances = []     # (name, super, iinit, traits)
        self.classes = []       # (cinit, traits)
        self.scripts = []       # (sinit, traits)
        self.bodies = {}        # method_id -> dict
        self._p = 0
        self.parse()

    def parse(self):
        d = self.d
        p = 4
        n, p = self._cnt(p)
        for _ in range(n):
            v, p = s32v(d, p)
            self.ints.append(v)
        n, p = self._cnt(p)
        for _ in range(n):
            v, p = u30(d, p)
            self.uints.append(v)
        n, p = self._cnt(p)
        for _ in range(n):
            self.dbls.append(struct.unpack_from('<d', d, p)[0])
            p += 8
        n, p = self._cnt(p)
        for _ in range(n):
            ln, p = u30(d, p)
            self.strs.append(d[p:p + ln].decode('utf-8', 'replace'))
            p += ln
        n, p = self._cnt(p)
        for _ in range(n):
            k, p = u8(d, p)
            i, p = u30(d, p)
            self.nss.append((k, i))
        n, p = self._cnt(p)
        for _ in range(n):
            c, p = u30(d, p)
            s2 = []
            for _ in range(c):
                x, p = u30(d, p)
                s2.append(x)
            self.ns_sets.append(s2)
        n, p = self._cnt(p)
        for _ in range(n):
            self.mnames.append(self._mn(p))
            p = self._p
        n, p = self._raw(p)                       # method_info
        for _ in range(n):
            # 顺序：param_count, return_type, param_type[], name, flags, [options], [param_names]
            pc, p = u30(d, p)
            ret, p = u30(d, p)
            for _ in range(pc):
                p = u30(d, p)[1]
            nm, p = u30(d, p)
            fl, p = u8(d, p)
            if fl & 0x08:                          # HAS_OPTIONAL
                c, p = u30(d, p)
                for _ in range(c):
                    p = u30(d, p)[1]
                    p = u8(d, p)[1]
            if fl & 0x80:                          # HAS_PARAM_NAMES
                for _ in range(pc):
                    p = u30(d, p)[1]
            self.methods.append([pc, ret, nm, fl])
        n, p = self._raw(p)                       # metadata
        for _ in range(n):
            p = u30(d, p)[1]
            c, p = u30(d, p)
            for _ in range(c):
                p = u30(d, p)[1]
                p = u30(d, p)[1]
        n, p = self._raw(p)                       # instance + class
        for _ in range(n):
            name, p = u30(d, p)
            sup, p = u30(d, p)
            fl, p = u8(d, p)
            if fl & 0x08:
                p = u30(d, p)[1]
            c, p = u30(d, p)
            for _ in range(c):
                p = u30(d, p)[1]
            iinit, p = u30(d, p)
            ntr, p = u30(d, p)
            tr, p = self._traits(p, ntr)
            self.instances.append((name, sup, iinit, tr))
        # class_info 是**独立的一整块**（不是紧跟每个 instance），漏这点会整段失步
        for _ in range(n):
            cinit, p = u30(d, p)
            ntr, p = u30(d, p)
            tr2, p = self._traits(p, ntr)
            self.classes.append((cinit, tr2))
        n, p = self._raw(p)                       # script
        for _ in range(n):
            sinit, p = u30(d, p)
            ntr, p = u30(d, p)
            tr, p = self._traits(p, ntr)
            self.scripts.append((sinit, tr))
        n, p = self._raw(p)                       # method_body
        for _ in range(n):
            mid, p = u30(d, p)
            p = u30(d, p)[1]                      # max_stack
            mx_local, p = u30(d, p)
            init_scope, p = u30(d, p)
            mx_scope, p = u30(d, p)
            clen, p = u30(d, p)
            code = d[p:p + clen]
            p += clen
            ne, p = u30(d, p)
            p += ne * 8
            ntr, p = u30(d, p)
            tr, p = self._traits(p, ntr)
            self.bodies[mid] = dict(code=code, locals=mx_local, init=init_scope,
                                    maxscope=mx_scope, traits=tr)
        self.end = p

    def _cnt(self, p):
        """常量池的 count 含索引 0（空表项）⇒ 条目 = count - 1。"""
        n, p = u30(self.d, p)
        return max(n - 1, 0), p

    def _raw(self, p):
        """method / metadata / class / script / body 的 count 是**实数**，不减 1。
        这里减 1 会让整段错位一位（我踩过：方法名全变 0、类数读成 0）。"""
        return u30(self.d, p)

    def _mn(self, p):
        d = self.d
        k, p = u8(d, p)
        if k in (0x07, 0x0D):                  # QName / QNameA
            ns, p = u30(d, p)
            nm, p = u30(d, p)
            rec = (k, ns, nm)
        elif k in (0x09, 0x0E):                # Multiname / MultinameA
            nm, p = u30(d, p)
            ns, p = u30(d, p)
            rec = (k, ns, nm)
        elif k in (0x0F, 0x10):                # RTQName(A)
            nm, p = u30(d, p)
            rec = (k, 0, nm)
        elif k in (0x11, 0x12):                # RTQNameL(A)
            rec = (k, 0, 0)
        elif k in (0x1B, 0x1C):                # MultinameL(A)
            ns, p = u30(d, p)
            rec = (k, ns, 0)
        elif k == 0x1D:                        # TypeName
            nm, p = u30(d, p)
            c, p = u30(d, p)
            for _ in range(c):
                p = u30(d, p)[1]
            rec = (k, 0, nm)
        else:
            raise ValueError('multiname kind %#x at %d' % (k, p))
        self._p = p
        return rec

    def _traits(self, p, ntr):
        d = self.d
        out = []
        for _ in range(ntr):
            nm, p = u30(d, p)
            k, p = u8(d, p)
            kind = k & 0x0F
            info = {}
            if kind in (0, 1, 2, 3):
                # Slot: slot_id, type_name, vindex, [vkind, vindex]
                # Method/Getter/Setter: disp_id, method（**没有 type 和 value**）
                sid, p = u30(d, p)
                mid, p = u30(d, p)
                info = dict(slot=sid, mid=mid)
                if kind == 0:
                    v, p = u30(d, p)
                    if v:
                        p = self._val(p, info)
            elif kind in (4, 6):
                sid, p = u30(d, p)
                info = dict(slot=sid)
                if kind == 4:
                    info['class'] = u30(d, p)[0]
                else:
                    info['type'] = u30(d, p)[0]
                    v, p = u30(d, p)
                    if v:
                        p = self._val(p, info)
            elif kind == 5:
                sid, p = u30(d, p)
                info = dict(slot=sid, mid=u30(d, p)[0])
            else:
                raise ValueError('trait kind %d at %d' % (kind, p))
            if k & 0x04:                      # ATTR_Metadata（不是 0x40，我踩过）
                c, p = u30(d, p)
                info['meta'] = [u30(d, p)[0] for _ in range(c)]
            out.append((nm, kind, info))
        return out, p

    def _val(self, p, info):
        d = self.d
        vk, p = u8(d, p)
        info['vkind'] = vk
        if vk == 0:
            ln, p = u30(d, p)
            info['vstr'] = d[p:p + ln].decode('utf-8', 'replace')
            p += ln
        elif vk in (1, 2):
            info['vnum'] = u30(d, p)[0]
        elif vk == 3:
            info['vnum'] = struct.unpack_from('<d', d, p)[0]
            p += 8
        elif vk == 4:
            info['vbool'] = d[p]
            p += 1
        elif vk in (5, 6):                     # Null / Undefined：无负载
            pass
        elif vk >= 7:                          # Namespace 家族：u8 kind + u30 name
            nk, p = u8(d, p)
            nm, p = u30(d, p)
            info['vns'] = (nk, nm)
        return p

    # ---- 名字 ----
    def s(self, i):
        return self.strs[i] if 0 <= i < len(self.strs) else '?%d' % i

    def mn(self, i):
        if i <= 0 or i > len(self.mnames):
            return '*'
        k, ns, nm = self.mnames[i - 1]
        name = self.s(nm) if nm else '*'
        if k == 0x09:
            return name + '{…}'
        return name


# ---------------- 反汇编 ----------------
OPS = {
    0x01: ('bkpt', 0), 0x02: ('nop', 0), 0x03: ('throw', 0), 0x04: ('getsuper', 'mn'),
    0x05: ('setsuper', 'mn'), 0x06: ('dxns', 'u30'), 0x07: ('dxnslate', 0),
    0x08: ('kill', 'u30'), 0x09: ('label', 0), 0x0C: ('ifnlt', 'br'),
    0x0D: ('ifnle', 'br'), 0x0E: ('ifngt', 'br'), 0x0F: ('ifnge', 'br'),
    0x10: ('jump', 'br'), 0x11: ('iftrue', 'br'), 0x12: ('iffalse', 'br'),
    0x13: ('ifeq', 'br'), 0x14: ('ifne', 'br'), 0x15: ('iflt', 'br'),
    0x16: ('ifle', 'br'), 0x17: ('ifgt', 'br'), 0x18: ('ifge', 'br'),
    0x19: ('ifstricteq', 'br'), 0x1A: ('ifstrictne', 'br'),
    0x1B: ('lookupswitch', 'sw'), 0x1C: ('pushwith', 0), 0x1D: ('popscope', 0),
    0x1E: ('nextname', 0), 0x1F: ('hasnext', 0), 0x20: ('pushnull', 0),
    0x21: ('pushundefined', 0), 0x23: ('nextvalue', 0), 0x24: ('pushbyte', 's8'),
    0x25: ('pushshort', 'u30'), 0x26: ('pushtrue', 0), 0x27: ('pushfalse', 0),
    0x28: ('pushnan', 0), 0x29: ('pop', 0), 0x2A: ('dup', 0), 0x2B: ('swap', 0),
    0x2C: ('pushstring', 'str'), 0x2D: ('pushint', 'int'), 0x2E: ('pushuint', 'uint'),
    0x2F: ('pushdouble', 'dbl'), 0x30: ('pushscope', 0), 0x31: ('pushnamespace', 'u30'),
    0x32: ('hasnext2', 'uu'), 0x35: ('li8', 0), 0x36: ('li16', 0), 0x37: ('li32', 0),
    0x38: ('lf32', 0), 0x39: ('lf64', 0), 0x3A: ('si8', 0), 0x3B: ('si16', 0),
    0x3C: ('si32', 0), 0x3D: ('sf32', 0), 0x3E: ('sf64', 0),
    0x40: ('newfunction', 'u30'), 0x41: ('call', 'u30'), 0x42: ('construct', 'u30'),
    0x43: ('callmethod', 'um'), 0x44: ('callstatic', 'um'), 0x45: ('callsuper', 'um'),
    0x46: ('callproperty', 'um'), 0x47: ('returnvoid', 0), 0x48: ('returnvalue', 0),
    0x49: ('constructsuper', 'u30'), 0x4A: ('constructprop', 'um'),
    0x4C: ('callproplex', 'um'), 0x4E: ('callsupervoid', 'um'),
    0x4F: ('callpropvoid', 'um'), 0x50: ('sxi1', 0), 0x51: ('sxi8', 0),
    0x52: ('sxi16', 0), 0x53: ('applytype', 'u30'), 0x55: ('newobject', 'u30'),
    0x56: ('newarray', 'u30'), 0x57: ('newactivation', 0), 0x58: ('newclass', 'u30'),
    0x59: ('getdescendants', 'mn'), 0x5A: ('newcatch', 'u30'),
    0x5D: ('findpropstrict', 'mn'), 0x5E: ('findproperty', 'mn'),
    0x5F: ('finddef', 'mn'), 0x60: ('getlex', 'mn'), 0x61: ('setproperty', 'mn'),
    0x62: ('getlocal', 'u30'), 0x63: ('setlocal', 'u30'), 0x64: ('getglobalscope', 0),
    0x65: ('getscopeobject', 'u30'), 0x66: ('getproperty', 'mn'),
    0x67: ('setpropertylate', 'mn'), 0x68: ('initproperty', 'mn'),
    0x6A: ('deleteproperty', 'mn'), 0x6C: ('getslot', 'u30'), 0x6D: ('setslot', 'u30'),
    0x6E: ('getglobalslot', 'u30'), 0x6F: ('setglobalslot', 'u30'),
    0x70: ('convert_s', 0), 0x71: ('esc_xelem', 0), 0x72: ('esc_xattr', 0),
    0x73: ('convert_i', 0), 0x74: ('convert_u', 0), 0x75: ('convert_d', 0),
    0x76: ('convert_b', 0), 0x77: ('convert_o', 0), 0x78: ('checkfilter', 0),
    0x80: ('coerce', 'mn'), 0x81: ('coerce_b', 0), 0x82: ('coerce_a', 0),
    0x83: ('coerce_i', 0), 0x84: ('coerce_d', 0), 0x85: ('coerce_s', 0),
    0x86: ('astype', 'mn'), 0x87: ('astypelate', 0), 0x88: ('coerce_u', 0),
    0x89: ('coerce_o', 0), 0x90: ('negate', 0), 0x91: ('increment', 0),
    0x92: ('inclocal', 'u30'), 0x93: ('decrement', 0), 0x94: ('declocal', 'u30'),
    0x95: ('typeof', 0), 0x96: ('not', 0), 0x97: ('bitnot', 0), 0xA0: ('add', 0),
    0xA1: ('subtract', 0), 0xA2: ('multiply', 0), 0xA3: ('divide', 0),
    0xA4: ('modulo', 0), 0xA5: ('lshift', 0), 0xA6: ('rshift', 0),
    0xA7: ('urshift', 0), 0xA8: ('bitand', 0), 0xA9: ('bitor', 0),
    0xAA: ('bitxor', 0), 0xAB: ('equals', 0), 0xAC: ('strictequals', 0),
    0xAD: ('lessthan', 0), 0xAE: ('lessequals', 0), 0xAF: ('greaterthan', 0),
    0xB0: ('greaterequals', 0), 0xB1: ('instanceof', 0), 0xB2: ('istype', 'mn'),
    0xB3: ('istypelate', 0), 0xB4: ('in', 0), 0xC0: ('increment_i', 0),
    0xC1: ('decrement_i', 0), 0xC2: ('inclocal_i', 'u30'), 0xC3: ('declocal_i', 'u30'),
    0xC4: ('negate_i', 0), 0xC5: ('add_i', 0), 0xC6: ('subtract_i', 0),
    0xC7: ('multiply_i', 0), 0xD0: ('getlocal0', 0), 0xD1: ('getlocal1', 0),
    0xD2: ('getlocal2', 0), 0xD3: ('getlocal3', 0), 0xD4: ('setlocal0', 0),
    0xD5: ('setlocal1', 0), 0xD6: ('setlocal2', 0), 0xD7: ('setlocal3', 0),
    0xEF: ('debug', 'dbg'), 0xF0: ('debugline', 'u30'), 0xF1: ('debugfile', 'u30'),
    0xF2: ('bkptline', 'u30'), 0xF3: ('timestamp', 0),
}


def disasm(abc, code):
    try:
        return _disasm(abc, code)
    except (IndexError, ValueError):
        return []


def _disasm(abc, code):
    p = 0
    out = []
    while p < len(code):
        at = p
        op = code[p]
        p += 1
        if op not in OPS:
            out.append((at, 'DBG(%02x)' % op))
            break
        name, kind = OPS[op]
        args = ''
        if kind == 0:
            pass
        elif kind == 'u30':
            v, p = u30(code, p)
            args = str(v)
        elif kind == 's8':
            v = code[p]
            p += 1
            args = str(v - 256 if v > 127 else v)
        elif kind == 'str':
            v, p = u30(code, p)
            args = '"%s"' % abc.s(v)
        elif kind == 'int':
            v, p = u30(code, p)
            args = 'int#%d=%s' % (v, abc.ints[v - 1] if 0 < v <= len(abc.ints) else '?')
        elif kind == 'uint':
            v, p = u30(code, p)
            args = 'uint#%d' % v
        elif kind == 'dbl':
            v, p = u30(code, p)
            args = 'dbl#%d' % v
        elif kind == 'mn':
            v, p = u30(code, p)
            args = abc.mn(v)
        elif kind == 'um':
            v, p = u30(code, p)
            ac, p = u30(code, p)
            args = '%s argc=%d' % (abc.mn(v), ac)
        elif kind == 'dbg':
            v, p = u30(code, p)
            ln2 = code[p]; p += 1
            rg = code[p]; p += 1
            args = 'file#%d line=%d reg=%d' % (v, ln2, rg)
        elif kind == 'uu':
            a, p = u30(code, p)
            b, p = u30(code, p)
            args = '%d,%d' % (a, b)
        elif kind == 'br':
            v = int.from_bytes(code[p:p + 3], 'little', signed=True)
            p += 3
            args = '@%04x' % (p + v)
        elif kind == 'sw':
            base = p
            dflt = int.from_bytes(code[p:p + 3], 'little', signed=True)
            p += 3
            cnt, p = u30(code, p)
            cases = []
            for _ in range(cnt + 1):
                v = int.from_bytes(code[p:p + 3], 'little', signed=True)
                p += 3
                cases.append(base + v)
            args = 'default=@%04x cases=%s' % (base + dflt,
                                               ','.join('@%04x' % c for c in cases[:8]))
        out.append((at, ('%-17s %s' % (name, args)).rstrip()))
    return out


def dump_method(abc, mid, indent='  '):
    b = abc.bodies.get(mid)
    if not b:
        print('%s--- method #%d  <无方法体>' % (indent, mid))
        return
    pc, ret, nm, fl = abc.methods[mid]
    print('%s--- method #%d  %s  params=%d locals=%d code=%dB' %
          (indent, mid, abc.s(nm), pc, b['locals'], len(b['code'])))
    for at, t in disasm(abc, b['code']):
        print('%s%04x  %s' % (indent, at, t))


def main():
    path = sys.argv[1]
    abcs = []
    for c, pl in swf_tags(load_swf(path)):
        if c != 82:
            continue
        # DoABC 头：flags(u30) + name(NUL 结尾)。本作写入器把 flags 写成 4 字节对齐的 u32，
        # 直接按 u30 会挪 3 字节 ⇒ 用「flags 后的第一个 00」定位名字结尾，再取 ABC 起点。
        off = pl.index(0, 4) + 1 if pl[:4] == b'\x01\x00\x00\x00' else 1
        abcs.append(pl[off:])
    print('DoABC count', len(abcs))
    a = ABC(abcs[0])
    if '--str' in sys.argv:
        key = sys.argv[sys.argv.index('--str') + 1]
        for i, s in enumerate(a.strs):
            if key in s:
                print('[%d] %r' % (i, s[:120]))
        return
    if '--class' in sys.argv:
        key = sys.argv[sys.argv.index('--class') + 1]
        for ci, (name, sup, iinit, tr) in enumerate(a.instances):
            full = a.mn(name)
            if key.lower() not in full.lower():
                continue
            print('=== class %s  (super %s)' % (full, a.mn(sup)))
            print('  traits:', [(a.s(n), k, v.get('mid')) for n, k, v in tr])
            if iinit:
                dump_method(a, iinit)
            for nmidx, kind, info in tr:
                if kind in (1, 2, 3):
                    dump_method(a, info['mid'])
        return
    if '--method' in sys.argv:
        dump_method(a, int(sys.argv[sys.argv.index('--method') + 1]))
        return
    print('strings', len(a.strs), 'methods', len(a.methods),
          'classes', len(a.instances), 'bodies', len(a.bodies),
          'parsed %d/%d' % (a.end, len(a.d)))


if __name__ == '__main__':
    main()
