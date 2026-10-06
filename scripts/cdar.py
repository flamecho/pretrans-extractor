import struct, zlib

def find_table(d):
    n = len(d)
    for base in (0x20, 0x40, 0x10):
        cnt_max = (n - base) // 16
        if cnt_max <= 0:
            continue
        recs = [struct.unpack_from('<IIII', d, base + 16 * i) for i in range(cnt_max)]
        best = 0
        for i, (no, pk, off, sz) in enumerate(recs):
            if no == 0 and pk == 0 and off == 0 and sz == 0:
                best = i          # terminator (empty record) still inside table
                continue
            if off == 0 and sz == 0:
                best = i + 1      # dir record
                continue
            if off + (pk >> 8) <= n and sz <= n:
                best = i + 1
                continue
            break
        if best >= 1:
            return base, best, recs[:best]
    return None


class Dar:
    def __init__(self, data):
        self.d = data
        r = find_table(data)
        if r is None:
            raise ValueError('no table')
        self.base, self.count, self.entries = r
        ver, self.total, self.unk = struct.unpack_from('<III', data, 4)
        self.root_count = struct.unpack_from('<I', data, 16)[0]

    def name(self, no):
        if not (0 < no < len(self.d)):
            return ''
        e = self.d.find(b'\x00', no)
        if e < 0 or e - no > 128:
            return ''
        try:
            return self.d[no:e].decode('cp932')
        except Exception:
            return ''

    def data_at(self, pk, off, sz):
        if not off or not sz:
            return b''
        blob = self.d[off:off + (pk >> 8)]
        if (pk & 0xFF) == 2:
            try:
                return zlib.decompress(blob)
            except Exception:
                return blob
        return blob

    def files(self):
        out = []
        for i, (no, pk, off, sz) in enumerate(self.entries):
            out.append((i, self.name(no), pk, off, sz))
        return out
