#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CRI CPK unpacker (v1 ITOC-style + v2/v3 @UTF), 纯 Python.

关键点（来自 CriPakTools CPK.cs）:
  0x00 'CPK '
  0x04 u32 unk1        (LE)
  0x08 u64 utf_size    (LE)  -> 之后 utf_size 字节是 CPK 头 @UTF (可能被 XOR 加密)
  @UTF 表字段: TocOffset / EtocOffset / ItocOffset / GtocOffset /
               ContentOffset / Files / Align
  各 TOC 段: 4 字节 magic ('TOC '/'ITOC'/'ETOC'/'GTOC') 之后同样跟
             u32 unk1 + u64 size + 加密的 @UTF。
  CPK 头/各 TOC 的 @UTF 若被加密，用 CRI UTF-XOR 解密:
      m=0x655f, t=0x4115, out[i]=in[i]^(m&0xff), m*=t   (32bit)
"""
import os
import sys
import struct

# ---------------- CRI UTF XOR ----------------
def utf_decrypt(buf):
    out = bytearray(buf)
    m = 0x655F
    for i in range(len(out)):
        out[i] ^= (m & 0xFF)
        m = (m * 0x4115) & 0xFFFFFFFF
    return bytes(out)

def is_encrypted(b):
    return not (len(b) >= 4 and b[0] == 0x40 and b[1] == 0x55 and b[2] == 0x54 and b[3] == 0x46)

# ---------------- @UTF table ----------------
TYPE_SIZE = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 8, 7: 8, 8: 4, 9: 8, 0x0A: 4, 0x0B: 4}
STORAGE_MASK = 0xF0
STORAGE_NONE = 0x00
STORAGE_ZERO = 0x10
STORAGE_CONST = 0x30
STORAGE_PERROW = 0x50
TYPE_MASK = 0x0F
TYPE_STRING = 0x0A

def u8(b, o): return b[o]
def u16(b, o): return struct.unpack_from('>H', b, o)[0]
def u32(b, o): return struct.unpack_from('>I', b, o)[0]

class UTF(object):
    def __init__(self, raw):
        assert raw[:4] == b'@UTF', raw[:4]
        self.raw = raw
        base = 8
        self.table_size = u32(raw, 4)
        self.rows_off = u32(raw, 8) + base
        self.strings_off = u32(raw, 0x0C) + base
        self.data_off = u32(raw, 0x10) + base
        self.table_name = self._str(u32(raw, 0x14), self.strings_off)
        self.num_cols = u16(raw, 0x18)
        self.row_len = u16(raw, 0x1A)
        self.num_rows = u32(raw, 0x1C)
        self.columns = []
        p = 0x20
        for _ in range(self.num_cols):
            flags = raw[p]
            name = self._str(u32(raw, p + 1), self.strings_off)
            p += 5
            storage = flags & STORAGE_MASK
            typ = flags & TYPE_MASK
            const = None
            if storage == STORAGE_CONST:
                const = self._value(raw, p, typ, self.data_off, self.strings_off)
                p += TYPE_SIZE.get(typ, 4)
            self.columns.append({'name': name, 'flags': flags,
                                 'storage': storage, 'type': typ, 'const': const})
        self.colpos = p
        self.rows = [self._row(i) for i in range(self.num_rows)]

    def _cstr(self, buf, off, base):
        if off == 0:
            return ''
        p = base + off
        if p < 0 or p >= len(buf):
            return ''
        end = buf.find(b'\x00', p)
        if end < 0:
            end = len(buf)
        return buf[p:end].decode('utf-8', 'replace')

    def _str(self, off, base):
        return self._cstr(self.raw, off, base)

    def _value(self, buf, off, typ, doff, soff):
        if typ == 0: return buf[off]
        if typ == 1: return struct.unpack_from('>b', buf, off)[0]
        if typ == 2: return u16(buf, off)
        if typ == 3: return struct.unpack_from('>h', buf, off)[0]
        if typ == 4: return u32(buf, off)
        if typ == 5: return struct.unpack_from('>i', buf, off)[0]
        if typ == 6: return struct.unpack_from('>Q', buf, off)[0]
        if typ == 7: return struct.unpack_from('>q', buf, off)[0]
        if typ == 8: return struct.unpack_from('>f', buf, off)[0]
        if typ == 9: return struct.unpack_from('>d', buf, off)[0]
        if typ == 0x0A:
            o = u32(buf, off)
            if o == 0:
                return ''
            # 字符串一般存在 data 区，回退 strings 区
            if doff + o < len(self.raw) and self.raw.find(b'\x00', doff + o) >= 0:
                return self._cstr(self.raw, o, doff)
            return self._cstr(self.raw, o, soff)
        if typ == 0x0B:
            # 数据区字节串：行内存 u32 offset（相对 data 区）。
            # 注意 offset=0 也有效（位于 data 区起始）。
            o = u32(buf, off)
            start = doff + o
            if start >= len(self.raw):
                return b''
            return bytes(self.raw[start:])
        return None

    def _row(self, i):
        off = self.rows_off + i * self.row_len
        rec = {}
        rel = 0
        for c in self.columns:
            st = c['storage']; typ = c['type']
            if st == STORAGE_PERROW:
                sz = TYPE_SIZE.get(typ, 4)
                rec[c['name']] = self._value(self.raw, off + rel, typ,
                                             self.data_off, self.strings_off)
                rel += sz
            elif st == STORAGE_CONST:
                rec[c['name']] = c['const']
            else:
                rec[c['name']] = b'' if typ == 0x0B else (0 if typ != TYPE_STRING else '')
        return rec


# ---------------- CRILAYLA ----------------
def crilayla_decompress(block):
    usize = struct.unpack_from('<I', block, 8)[0]
    csize = struct.unpack_from('<I', block, 12)[0]
    src = block[16:16 + csize]
    out = bytearray(block[16 + csize:16 + csize + 0x100])
    out += bytearray(usize)
    sp = csize - 1
    dp = len(out) - 1
    dst_end = 0x100
    bitcnt = 0
    bitdat = 0

    def get_bits(n):
        nonlocal sp, bitcnt, bitdat
        if bitcnt < n:
            cnt = ((24 - bitcnt) >> 3) + 1
            bitcnt += cnt * 8
            bitdat = (bitdat << (cnt * 8)) | int.from_bytes(src[sp - cnt + 1:sp + 1], 'big')
            sp -= cnt
        r = (bitdat >> (bitcnt - n)) & ((1 << n) - 1)
        bitcnt -= n
        return r

    while dp >= dst_end:
        if get_bits(1):
            off = get_bits(13) + 3
            cnt = get_bits(8) + 3
            p = dp + off
            for _ in range(cnt):
                out[dp] = out[p]
                dp -= 1
                p -= 1
        else:
            out[dp] = get_bits(8)
            dp -= 1
    return bytes(out)


# ---------------- CPK reader ----------------
class CPK(object):
    def __init__(self, path):
        self.path = path
        self.f = open(path, 'rb')
        self.entries = []
        self._read_header()
        self._read_tocs()

    def _read(self, off, size):
        self.f.seek(off)
        return self.f.read(size)

    def _read_utf_at(self, pos):
        """从 pos 处读取 @UTF 段（含可能的加密）。返回 (UTF obj, 原始解密后字节)。"""
        magic = self._read(pos, 4)
        # 若 magic 不是已知段头，则 pos 直接就是 @UTF
        if magic in (b'@UTF',):
            hdr = self._read(pos, 0x10)
        else:
            hdr = self._read(pos, 0x10)
            # magic + u32 unk1(LE) + u64 size(LE)
        if magic == b'@UTF':
            raw = self._read(pos, u32(self._read(pos, 4), 0) + 8)
        unk1 = struct.unpack_from('<I', hdr, 4)[0]
        size = struct.unpack_from('<Q', hdr, 8)[0]
        payload = self._read(pos + 0x10, size)
        if is_encrypted(payload):
            payload = utf_decrypt(payload)
        return UTF(payload), payload

    def _read_header(self):
        if self._read(0, 4) != b'CPK ':
            raise ValueError('not a CPK')
        # CPK: magic(4) + unk1 u32(LE)@0x04 + utf_size u64(LE)@0x08 + @UTF@0x10
        hdr = self._read(4, 0xC)
        unk1 = struct.unpack_from('<I', hdr, 0)[0]
        size = struct.unpack_from('<Q', hdr, 4)[0]
        payload = self._read(0x10, size)
        if is_encrypted(payload):
            payload = utf_decrypt(payload)
        self.hdr_utf = UTF(payload)
        r = self.hdr_utf.rows[0]
        self.TocOffset = r.get('TocOffset')
        self.ItocOffset = r.get('ItocOffset')
        self.GtocOffset = r.get('GtocOffset')
        self.EtocOffset = r.get('EtocOffset')
        self.ContentOffset = r.get('ContentOffset')
        self.Align = r.get('Align', 1) or 1
        self.Files = r.get('Files')

    def _read_tocs(self):
        if self.ItocOffset not in (None, 0xFFFFFFFFFFFFFFFF, 0):
            self._read_itoc(self.ItocOffset)
        if self.TocOffset not in (None, 0xFFFFFFFFFFFFFFFF, 0):
            self._read_toc(self.TocOffset)
        if self.GtocOffset not in (None, 0xFFFFFFFFFFFFFFFF, 0):
            pass  # GTOC 只含名字表，忽略

    def _read_itoc(self, pos):
        itoc_utf, _ = self._read_utf_at(pos)
        r = itoc_utf.rows[0]
        DataL = r.get('DataL')
        DataH = r.get('DataH')
        sizes = {}
        csizes = {}
        ids = []
        for blob in (DataL, DataH):
            if not isinstance(blob, (bytes, bytearray)) or len(blob) < 4:
                continue
            if blob[:4] != b'@UTF':
                continue
            sub = UTF(blob)
            for row in sub.rows:
                fid = row.get('ID')
                if fid is None:
                    continue
                sizes[fid] = row.get('FileSize', 0) or 0
                if 'ExtractSize' in row:
                    csizes[fid] = row.get('ExtractSize', 0) or 0
                ids.append(fid)
        ids = sorted(set(ids))
        base = self.ContentOffset or 0
        align = self.Align or 1
        for fid in ids:
            size = sizes.get(fid, 0)
            self.entries.append({
                'name': None, 'id': fid,
                'FileSize': size,
                'ExtractSize': csizes.get(fid, size),
                'offset': base,
            })
            if align > 1 and (size % align):
                base += size + (align - (size % align))
            else:
                base += size

    def _read_toc(self, pos):
        toc_utf, _ = self._read_utf_at(pos)
        for row in toc_utf.rows:
            nm = row.get('FileName', '')
            did = row.get('DirName', '')
            if not nm:
                continue
            name = (did + '/' + nm) if did else nm
            self.entries.append({
                'name': name, 'id': row.get('ID'),
                'FileSize': row.get('FileSize', 0) or 0,
                'ExtractSize': row.get('ExtractSize', row.get('FileSize', 0)) or 0,
                'offset': (row.get('FileOffset', 0) or 0) + (self.ContentOffset or 0),
            })

    def raw(self, e):
        self.f.seek(e['offset'])
        data = self.f.read(e['FileSize'])
        if data[:8] == b'CRILAYLA':
            try:
                data = crilayla_decompress(data)
            except Exception as ex:
                sys.stderr.write('  [warn] CRILAYLA fail %s: %s\n' % (e.get('name'), ex))
        return data

    def extract(self, outdir, pred=None):
        os.makedirs(outdir, exist_ok=True)
        n = 0
        for e in self.entries:
            name = e['name']
            if name is None:
                name = '%04d' % (e['id'] if e['id'] is not None else n)
            if pred and not pred(name):
                continue
            name = name.replace('\\', '/').lstrip('/')
            dst = os.path.join(outdir, *name.split('/'))
            os.makedirs(os.path.dirname(dst) or outdir, exist_ok=True)
            with open(dst, 'wb') as o:
                o.write(self.raw(e))
            n += 1
        return n


if __name__ == '__main__':
    src = sys.argv[1]
    cpk = CPK(src)
    print('TocOffset=%s ItocOffset=%s ContentOffset=%s Align=%s Files=%s' % (
        cpk.TocOffset, cpk.ItocOffset, cpk.ContentOffset, cpk.Align, cpk.Files))
    print('entries:', len(cpk.entries))
    for e in cpk.entries[:15]:
        print('  ', e['name'], e['FileSize'], e['ExtractSize'], hex(e['offset']))
    if len(sys.argv) > 2:
        print('extracted:', cpk.extract(sys.argv[2]))
