#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CRI CPK unpacker (纯 Python, 无依赖)."""
import os
import sys
import struct
import zlib

STORAGE_MASK = 0xF0
STORAGE_NONE = 0x00
STORAGE_ZERO = 0x10
STORAGE_CONST = 0x30   # 常量值紧跟列定义之后
STORAGE_PERROW = 0x50

TYPE_MASK = 0x0F
TYPE_U8, TYPE_S8, TYPE_U16, TYPE_S16 = 0, 1, 2, 3
TYPE_U32, TYPE_S32, TYPE_U64, TYPE_S64 = 4, 5, 6, 7
TYPE_FLOAT, TYPE_DOUBLE, TYPE_STRING = 8, 9, 0x0A
TYPE_DATA = 0x0B

TYPE_SIZE = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 8, 7: 8, 8: 4, 9: 8,
             0x0A: 4, 0x0B: 8}


def u32(b, o):
    return struct.unpack_from('>I', b, o)[0]


def u16(b, o):
    return struct.unpack_from('>H', b, o)[0]


def utf_decrypt(buf):
    """CRI 的 LCG-XOR UTF 加密 -> 原地解密（若已是明文则原样返回）。"""
    m = 0x655f
    t = 0x4115
    out = bytearray(buf)
    for i in range(len(out)):
        out[i] ^= m & 0xFF          # ★ CriPakTools 用的是 m & 0xFF（非 >>8）
        m = (m * t) & 0xFFFFFFFF
    return bytes(out)


class UTF(object):
    def __init__(self, data, pos=0):
        self.pos = pos
        raw = data[pos:]
        if raw[:4] != b'@UTF':
            if raw[:4] in (b'TOC ', b'ITOC', b'ETOC', b'GTOC', b'CPK '):
                raw = raw[0x10:]          # 区段头，@UTF 在 +0x10
                pos += 0x10
            elif raw[:4] == b'CRILAYLA':
                raise ValueError('CRILAYLA at %#x' % pos)
        if raw[:4] != b'@UTF':
            dec = utf_decrypt(raw)        # CRI LCG-XOR 加密的 @UTF 表
            if dec[:4] == b'@UTF':
                raw = dec
        self.raw = raw
        self.table_size = u32(raw, 4)
        base = 8  # 所有内部偏移相对 raw+8
        self.rows_off = u32(raw, 8) + base
        self.strings_off = u32(raw, 0x0C) + base
        self.data_off = u32(raw, 0x10) + base
        self.table_name = self._str(u32(raw, 0x14))
        self.num_cols = u16(raw, 0x18)
        self.row_len = u16(raw, 0x1A)
        self.num_rows = u32(raw, 0x1C)
        self.columns = []
        p = 0x20
        for _ in range(self.num_cols):
            flags = raw[p]
            name = self._str(u32(raw, p + 1))
            p += 5
            storage = flags & STORAGE_MASK
            typ = flags & TYPE_MASK
            const = None
            if storage == STORAGE_CONST:
                const = self._value(raw, p, typ)
                p += TYPE_SIZE.get(typ, 4)
            self.columns.append({'name': name, 'flags': flags,
                                 'storage': storage, 'type': typ,
                                 'const': const})
        self.colpos = p
        self.rows = [self._row(i) for i in range(self.num_rows)]

    def _cstr(self, base, off):
        if off == 0:
            return ''
        p = base + off
        if p < 0 or p >= len(self.raw):
            return ''
        end = self.raw.find(b'\x00', p)
        if end < 0:
            end = len(self.raw)
        return self.raw[p:end].decode('utf-8', 'replace')

    def _str(self, off):
        return self._cstr(self.strings_off, off)

    def _svalue(self, buf, off):
        """行内字符串值：优先 data_off，越界/异常时回退 strings_off。"""
        o = u32(buf, off)
        if o == 0:
            return ''
        if self.data_off + o < len(self.raw) and \
                self.raw.find(b'\x00', self.data_off + o) >= 0:
            return self._cstr(self.data_off, o)
        return self._cstr(self.strings_off, o)

    def _value(self, buf, off, typ):
        if typ in (TYPE_U8,):
            return buf[off]
        if typ in (TYPE_S8,):
            return struct.unpack_from('>b', buf, off)[0]
        if typ in (TYPE_U16,):
            return u16(buf, off)
        if typ in (TYPE_S16,):
            return struct.unpack_from('>h', buf, off)[0]
        if typ in (TYPE_U32,):
            return u32(buf, off)
        if typ in (TYPE_S32,):
            return struct.unpack_from('>i', buf, off)[0]
        if typ in (TYPE_U64,):
            return struct.unpack_from('>Q', buf, off)[0]
        if typ in (TYPE_S64,):
            return struct.unpack_from('>q', buf, off)[0]
        if typ in (TYPE_FLOAT,):
            return struct.unpack_from('>f', buf, off)[0]
        if typ in (TYPE_DOUBLE,):
            return struct.unpack_from('>d', buf, off)[0]
        if typ == TYPE_STRING:
            return self._svalue(buf, off)
        if typ == TYPE_DATA:
            rel = u32(buf, off)
            size = u32(buf, off + 4)
            p = self.data_off + rel
            return bytes(self.raw[p:p + size])
        return None

    def _row(self, i):
        off = self.rows_off + i * self.row_len
        rec = {}
        rel = 0
        for c in self.columns:
            st = c['storage']
            typ = c['type']
            if st == STORAGE_PERROW:
                sz = TYPE_SIZE.get(typ, 4)
                rec[c['name']] = self._value(self.raw, off + rel, typ)
                rel += sz
            elif st == STORAGE_CONST:
                rec[c['name']] = c['const']
            else:  # ZERO(0x10) / NONE(0x00)
                rec[c['name']] = 0 if typ != TYPE_STRING else ''
        return rec


def align(v, a):
    return (v + a - 1) // a * a if a > 1 else v


def crilayla_decompress(block):
    """CRILAYLA 解压（算法来自 tpu / PyCriCodecs）。

    block 布局: 'CRILAYLA' + u32 decompress_size + u32 compressed_size
                + LZ 流(compressed_size) + 0x100 字节原文头
    输出 = 0x100 原文头 + LZ 解压出的 decompress_size 字节
    """
    usize = struct.unpack_from('<I', block, 8)[0]
    csize = struct.unpack_from('<I', block, 12)[0]
    src = block[16:16 + csize]          # LZ 流
    out = bytearray(block[16 + csize:16 + csize + 0x100])   # 前 0x100 字节原文
    out += bytearray(usize)             # 待解压区
    # 从尾部往前解码
    sp = csize - 1                      # src 读指针（递减）
    dp = len(out) - 1                   # out 写指针（递减）
    dst_end = 0x100                     # 解压区的起始下标
    bitcnt = 0
    bitdat = 0
    M32 = 0xFFFFFFFF

    def get_bits(n):
        nonlocal sp, bitcnt, bitdat
        if bitcnt < n:
            cnt = ((24 - bitcnt) >> 3) + 1
            bitcnt += cnt * 8
            for _ in range(cnt):
                bitdat = ((bitdat << 8) | src[sp]) & M32
                sp -= 1
        d = (bitdat >> (bitcnt - n)) & ((1 << n) - 1)
        bitcnt -= n
        return d

    while True:
        if get_bits(1) == 0:
            out[dp] = get_bits(8)
            dp -= 1
            if dp + 1 == dst_end:
                break
        else:
            poffset = get_bits(13)
            plen = get_bits(2)
            if plen == 3:
                plen += get_bits(3)
                if plen == 10:
                    plen += get_bits(5)
                    if plen == 41:
                        while True:
                            b = get_bits(8)
                            plen += b
                            if b != 255:
                                break
            pbuf = dp + poffset + 3
            plen += 3
            while plen:
                out[dp] = out[pbuf]
                pbuf -= 1
                dp -= 1
                plen -= 1
                if dp + 1 == dst_end:
                    break
            if dp + 1 == dst_end:
                break
    return bytes(out)


class CPK(object):
    def __init__(self, path):
        self.path = path
        self.f = open(path, 'rb')
        self.hdr = UTF(self._read(0x10, 0x400), 0).rows[0]
        self.files = []
        self._build()

    def _read(self, off, size):
        self.f.seek(off)
        return self.f.read(size)

    def _build(self):
        h = self.hdr
        self.content_off = h.get('ContentOffset', 0)
        self.align = h.get('Align', 0) or 1
        entries = []
        named = False
        # ---- TOC（含文件名）----
        if h.get('TocOffset'):
            t = UTF(self._read(h['TocOffset'], h['TocSize']), 0)
            self.toc = t
            for r in t.rows:
                nm = r.get('FileName', '')
                did = r.get('DirName', '')
                if isinstance(nm, str) and nm:
                    name = (did + '/' + nm) if did else nm
                    named = True
                else:
                    name = None
                entries.append({
                    'name': name,
                    'dir': did, 'file': nm,
                    'FileSize': r.get('FileSize', 0),
                    'ExtractSize': r.get('ExtractSize', 0),
                    'offset': r.get('FileOffset', 0),
                    'id': r.get('ID'),
                })
        # ---- ITOC ----
        if h.get('ItocOffset'):
            try:
                it = UTF(self._read(h['ItocOffset'], h['ItocSize']), 0)
                self.itoc = it
                for r in it.rows:
                    fl = r.get('FilesL')
                    fh = r.get('FilesH')
                    dl = r.get('DataL')
                    dh = r.get('DataH')
                    # 旧式：FilesL/FilesH 直接是子表（含 ID/FileSize）
                    for sub in (fl, fh):
                        if isinstance(sub, dict):
                            self._add_itoc(entries, sub, dl)
                    # 新式：DataL/DataH 是 byte blob（内嵌 @UTF 子表，含 ID/FileSize）
                    for sub in (dl, dh):
                        if isinstance(sub, (bytes, bytearray)) and sub[:4] == b'@UTF':
                            self._add_itoc_blob(entries, bytes(sub))
                        elif isinstance(sub, dict):
                            self._add_itoc(entries, sub, None)
            except Exception as e:
                print('  [warn] ITOC parse failed:', e)

        if named:
            # FileOffset 的基准：以最小 FileOffset 对齐到 ContentOffset
            base = min(e['offset'] for e in entries)
            for e in entries:
                e['offset'] += self.content_off - base
        else:
            # 无文件名 TOC：按 ID 升序顺序排布，尺寸对齐 Align
            ids = {}
            for e in entries:
                if e.get('id') is not None and e.get('offset') is None:
                    ids[e['id']] = e
            base = self.content_off
            for fid in sorted(ids):
                e = ids[fid]
                e['offset'] = base
                e['name'] = '%04d' % fid
                e['file'] = '%04d' % fid
                e['dir'] = ''
                fsz = e['FileSize'] or 0
                base += fsz if (fsz % self.align) == 0 else fsz + (self.align - fsz % self.align)
            entries = [e for e in entries if e.get('offset') is not None]

        end = max((e['offset'] + e['FileSize'] for e in entries), default=self.content_off)
        self.span = (self.content_off, end)
        self.entries = entries

    def _add_itoc(self, entries, sub, dmap):
        fid = sub.get('ID')
        fsz = sub.get('FileSize', 0)
        esz = sub.get('ExtractSize', fsz)
        entries.append({
            'name': None, 'file': None, 'dir': None,
            'FileSize': fsz, 'ExtractSize': esz,
            'offset': None, 'id': fid,
        })

    def _add_itoc_blob(self, entries, blob):
        """DataL/DataH 内嵌 @UTF 子表：ID -> FileSize/ExtractSize。"""
        sub = UTF(blob, 0)
        for r in sub.rows:
            fid = r.get('ID')
            if fid is None:
                continue
            fsz = r.get('FileSize') or 0
            esz = r.get('ExtractSize') or fsz
            entries.append({
                'name': None, 'file': None, 'dir': None,
                'FileSize': fsz, 'ExtractSize': esz,
                'offset': None, 'id': fid,
            })

    def raw(self, e):
        self.f.seek(e['offset'])
        data = self.f.read(e['FileSize'])
        if data[:8] == b'CRILAYLA':
            if e['ExtractSize'] and e['ExtractSize'] != e['FileSize']:
                try:
                    data = crilayla_decompress(data)
                except Exception as ex:
                    print('  [warn] CRILAYLA fail', e['name'], ex)
        return data

    def extract(self, outdir, pred=None):
        os.makedirs(outdir, exist_ok=True)
        n = 0
        for e in self.entries:
            if not e.get('name'):
                continue
            if pred and not pred(e['name']):
                continue
            name = e['name'].replace('\\', '/').lstrip('/')
            dst = os.path.join(outdir, *name.split('/'))
            os.makedirs(os.path.dirname(dst) or outdir, exist_ok=True)
            with open(dst, 'wb') as o:
                o.write(self.raw(e))
            n += 1
        return n

    def extract_all(self, outdir):
        return self.extract(outdir)


if __name__ == '__main__':
    src = sys.argv[1]
    cpk = CPK(src)
    print('CPK header:', src)
    for k, v in cpk.hdr.items():
        if v not in (0, '', None):
            print('   %-18s %s' % (k, hex(v) if isinstance(v, int) else v))
    print('entries:', len(cpk.entries))
    for e in cpk.entries[:15]:
        print('   ', e)
    if len(sys.argv) > 2:
        print('extracted:', cpk.extract_all(sys.argv[2]))
