"""GsWin「DataPack5」/ `.scw` 读取器（メサイア / 復讐帝國 之后同族引擎通用件）。

格式来源：`GsPak.py`（xorxorrax/gspak，zlib 许可）＋ 本机实测校正（2026-11-01）。

PAK 头 0x48：
    magic[0x10]="DataPack5"  desc[0x20]  u16 minor  u16 major
    u32 idx_length  u32 flags  u32 entries  u32 data_offset  u32 index_offset
索引（在 index_offset）：**LZSS 压缩**（可选先做 `i & 0xFF` XOR），解出后是 entries × 0x68：
    name[0x40] cp932 + u32 offset + u32 length + pad[0x20]
文件内容在 data_offset + offset，长度 length。

SCW（每条）：头 0x3C = `16s 4x i32 compressed, u32 uncompressed_len, u32 compressed_len,
    u32 instr_cnt, u32 string_cnt, u32 label_cnt, u32 instr_len, u32 string_len, u32 label_len`
    数据从 0x1C8 起；compressed == -1 ⇒ 先 `i&0xFF` XOR 再 LZSS 解，否则 XOR 后取 uncompressed_len 字节。
    解出的结构：三张表（instr/string/label，各 (u32,u32) 或 (u32,u32)）+ 三段数据。
"""
import struct


# ---------------- LZSS（Okumura 1989 / PyLZSS 同型） ----------------
# 解码：环形缓冲 N=4096、初始填充 init、起点 r=N-F(=4078)；
# 每字节 8 个 flag 位（LSB 先）；bit=1 ⇒ 原字节，bit=0 ⇒ 2 字节：
#   位置 i = b1 | ((b2 & 0xF0) << 4)   ← b1 是低 8 位，b2 的高 4 位是高位
#   长度   = (b2 & 0x0F) + 3
N = 4096
F = 18
INIT_R = N - F


def lzss_decompress(src, init=0):
    buf = bytearray([init & 0xFF] * N)
    r = INIT_R
    out = bytearray()
    p = 0
    n = len(src)
    flags = 0
    while True:
        flags >>= 1
        if (flags & 0x100) == 0:
            if p >= n:
                break
            flags = src[p] | 0xFF00
            p += 1
        if flags & 1:
            if p >= n:
                break
            c = src[p]
            p += 1
            out.append(c)
            buf[r] = c
            r = (r + 1) & (N - 1)
        else:
            if p + 1 >= n:
                break
            b1 = src[p]
            b2 = src[p + 1]
            p += 2
            i = b1 | ((b2 & 0xF0) << 4)
            ln = (b2 & 0x0F) + 3
            for k in range(ln):
                c = buf[(i + k) & (N - 1)]
                out.append(c)
                buf[r] = c
                r = (r + 1) & (N - 1)
    return bytes(out)


def xor_i(data):
    b = bytearray(data)
    for i in range(len(b)):
        b[i] ^= (i & 0xFF)
    return bytes(b)


# ---------------- PAK ----------------
class Pak:
    def __init__(self, path, encrypted=False):
        self.path = path
        self.encrypted = encrypted
        with open(path, 'rb') as f:
            d = f.read()
        self.raw = d
        (magic, desc, minor, major, idx_len, flags, entries,
         data_off, idx_off) = struct.unpack_from('<16s32sHHIIIII', d, 0)
        self.magic = magic.rstrip(b'\x00')
        self.desc = desc.rstrip(b'\x00').decode('cp932', 'replace')
        self.version = (minor, major)
        self.idx_len = idx_len
        self.flags = flags
        self.entries_count = entries
        self.data_off = data_off
        self.idx_off = idx_off
        self.entries = []
        self._read_index()

    def _read_index(self):
        blob = self.raw[self.idx_off:self.idx_off + self.idx_len]
        if self.encrypted:
            blob = xor_i(blob)
        idx = lzss_decompress(blob)
        p = 0
        for _ in range(self.entries_count):
            name = idx[p:p + 0x40].split(b'\x00')[0].decode('cp932', 'replace')
            off, ln = struct.unpack_from('<II', idx, p + 0x40)
            self.entries.append((name, off, ln))
            p += 0x68

    def read(self, name):
        for n, off, ln in self.entries:
            if n == name:
                s = self.data_off + off
                return self.raw[s:s + ln]
        raise KeyError(name)


# ---------------- SCW ----------------
class Scw:
    def __init__(self, data):
        self.data = data
        (self.magic, self.compressed, self.uncompressed_len, self.compressed_len,
         self.instr_cnt, self.string_cnt, self.label_cnt,
         self.instr_len, self.string_len, self.label_len) = \
            struct.unpack_from('<16s4xiII4xIIIIII', data, 0)
        self._parse()

    def _raw(self):
        body = self.data[0x1C8:]
        body = xor_i(body)
        if self.compressed == -1:
            return lzss_decompress(body)
        return body[:self.uncompressed_len]

    def _parse(self):
        blob = self._raw()
        p = 0
        instr_pairs = []
        for _ in range(self.instr_cnt):
            instr_pairs.append(struct.unpack_from('<II', blob, p)); p += 8
        str_pairs = []
        for _ in range(self.string_cnt):
            str_pairs.append(struct.unpack_from('<II', blob, p)); p += 8
        lbl_pairs = []
        for _ in range(self.label_cnt):
            lbl_pairs.append(struct.unpack_from('<II', blob, p)); p += 8
        self.instructions = []
        for off, ln in instr_pairs:
            self.instructions.append(blob[p:p + ln]); p += ln
        self.strings = []
        for off, ln in str_pairs:
            raw = blob[p:p + ln]; p += ln
            self.strings.append(raw.split(b'\x00')[0].decode('cp932', 'replace'))
        self.labels = []
        lb = blob[p:p + self.label_len]
        for s in lb.split(b'\x00'):
            if s:
                self.labels.append(s.decode('cp932', 'replace'))


if __name__ == '__main__':
    import sys
    pak = Pak(sys.argv[1], encrypted=('--xor' in sys.argv))
    print('%s  desc=%r  v%d.%d  entries=%d  data@%#x idx@%#x len=%d'
          % (pak.path.split('\\')[-1], pak.desc, pak.version[0], pak.version[1],
             pak.entries_count, pak.data_off, pak.idx_off, pak.idx_len))
    for n, off, ln in pak.entries[:10]:
        print('  %-24s off=%-8d len=%-8d' % (n, off, ln))
