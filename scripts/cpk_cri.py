"""CRI CPK (@UTF) 容器读取器 —— 最小可用实现（实测格式）。

NS 版 うたプリ Repeat LOVE 等用 CRI CPK 打包（`CPK ` 魔数 + @UTF 表）。

实测 @UTF 布局（本作 CPK v3）：
    +0x00 "@UTF" | +0x04 table_size
    之后所有 offset 均相对 base+8：
        +0x08 rows_off | +0x0c str_off | +0x10 data_off | +0x14 name_off
        +0x18 ncols(u16) | +0x1a rowlen(u16) | +0x1c nrows(u32)
    +0x20 起是列定义，每列：flags(u8) [+ name(u32) if flags&0x10] [+ const(u32) if flags&0x20]
        type = flags & 0x0F
    string 表基址 = base + 8 + str_off；行数据基址 = base + 8 + rows_off

用法：
    python scripts/cpk_cri.py <file.cpk>                 # 列表
    python scripts/cpk_cri.py <file.cpk> --extract DIR   # 导出
"""
import os
import struct
import sys

TYPE_SIZE = {0x00: 1, 0x01: 1, 0x02: 2, 0x03: 2, 0x04: 4, 0x05: 4,
             0x06: 8, 0x07: 8, 0x08: 4, 0x09: 8, 0x0A: 4, 0x0B: 8}


class UTF:
    def __init__(self, buf, base=0):
        self.buf = buf
        self.base = base
        assert buf[base:base + 4] == b'@UTF', 'not @UTF'
        self.table_size = struct.unpack_from('>I', buf, base + 4)[0]
        o = base + 8
        rows_off, str_off, data_off, name_off = struct.unpack_from('>IIII', buf, o)
        ncol, self.rowlen = struct.unpack_from('>HH', buf, o + 16)
        self.nrow = struct.unpack_from('>I', buf, o + 20)[0]
        self.rows_off = base + 8 + rows_off
        self.str_off = base + 8 + str_off
        self.data_off = base + 8 + data_off
        self.ncol = ncol
        p = base + 0x20
        self.cols = []
        for _ in range(ncol):
            flags = buf[p]
            p += 1
            name = None
            if flags & 0x10:
                no = struct.unpack_from('>I', buf, p)[0]
                p += 4
                name = self._str(self.str_off + no)
            const = None
            if flags & 0x20:
                const = struct.unpack_from('>I', buf, p)[0]
                p += 4
            self.cols.append({'name': name, 'type': flags & 0x0F,
                              'flags': flags, 'const': const, 'off': 0})
        off = 0
        for c in self.cols:
            c['off'] = off
            off += TYPE_SIZE[c['type']]
        self.calc_rowlen = off

    def _str(self, off):
        end = self.buf.find(b'\x00', off)
        return self.buf[off:end].decode('utf-8', 'replace')

    def value(self, row, i):
        c = self.cols[i]
        t = c['type']
        if c['const'] is not None:
            p = self.data_off + c['const']
        else:
            p = self.rows_off + row * self.rowlen + c['off']
        if t == 0x00:
            return self.buf[p]
        if t == 0x01:
            return struct.unpack_from('>b', self.buf, p)[0]
        if t == 0x02:
            return struct.unpack_from('>H', self.buf, p)[0]
        if t == 0x03:
            return struct.unpack_from('>h', self.buf, p)[0]
        if t == 0x04:
            return struct.unpack_from('>I', self.buf, p)[0]
        if t == 0x05:
            return struct.unpack_from('>i', self.buf, p)[0]
        if t == 0x06:
            return struct.unpack_from('>Q', self.buf, p)[0]
        if t == 0x07:
            return struct.unpack_from('>q', self.buf, p)[0]
        if t == 0x08:
            return struct.unpack_from('>f', self.buf, p)[0]
        if t == 0x09:
            return struct.unpack_from('>d', self.buf, p)[0]
        if t == 0x0A:
            return self._str(self.str_off + struct.unpack_from('>I', self.buf, p)[0])
        if t == 0x0B:
            do, ds = struct.unpack_from('>II', self.buf, p)
            return (self.data_off + do, ds)
        return None

    def rows(self):
        return [{c['name']: self.value(r, i) for i, c in enumerate(self.cols)}
                for r in range(self.nrow)]


class CPK:
    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            self.buf = f.read()
        assert self.buf[:4] == b'CPK ', 'not CPK'
        self.hdr = UTF(self.buf, 0x10)
        self.header = self.hdr.rows()[0]
        self.content_off = self.header.get('ContentOffset', 0)
        toc_off = self.header.get('TocOffset', 0)
        self.toc = UTF(self.buf, toc_off)
        self.entries = []
        for row in self.toc.rows():
            nm = row.get('FileName') or ''
            dn = row.get('DirName') or ''
            self.entries.append({'name': (dn + '/' + nm) if dn else nm,
                                 'offset': row.get('FileOffset', 0),
                                 'size': row.get('FileSize', 0),
                                 'id': row.get('ID')})

    def read(self, e):
        p = self.content_off + e['offset']
        return self.buf[p:p + e['size']]

    def extract(self, outdir, pred=None):
        n = 0
        for e in self.entries:
            if pred and not pred(e['name']):
                continue
            dst = os.path.join(outdir, e['name'].lstrip('/').replace('\\', '/'))
            os.makedirs(os.path.dirname(dst) or outdir, exist_ok=True)
            with open(dst, 'wb') as fo:
                fo.write(self.read(e))
            n += 1
        return n


if __name__ == '__main__':
    c = CPK(sys.argv[1])
    print(f'{sys.argv[1]}: {len(c.entries)} 条目  Content@{c.content_off:#x}  '
          f'Toc@{c.header.get("TocOffset"):#x}  行宽={c.toc.rowlen}')
    if '--extract' in sys.argv:
        d = sys.argv[sys.argv.index('--extract') + 1]
        print('导出', c.extract(d), '个到', d)
    else:
        for e in c.entries[:40]:
            print(f'  {e["name"]:<48} {e["size"]:>12,}')
