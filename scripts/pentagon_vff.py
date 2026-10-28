# -*- coding: utf-8 -*-
"""LiveMaker VFF 资源包解包（Pentagon Syndrome / 单 exe 全内嵌）

格式（GARbro ArcVF.cs）：
  base = PE overlay 起点
  0x00 'vff\0'
  0x06 u32 count
  0x0A 逐条：[u32 nameLen][nameLen 字节, 与 TpRandom(0x75D6EE39) 逐字节 XOR 后为 cp932]
  之后：count+1 个 int64 offset，各 XOR (int)TpRandom 下一值；entry.Size = next-off
  最后：每 entry 1 字节 flags：0/3=zlib, 2/3=scrambled
  scrambled: 前 8 字节 = [i32 chunkSize][u32 seed^0xF8EA]，按 TpScramble 随机序重排块
"""
import struct, sys, os, zlib

MASK = 0xFFFFFFFF


class TpRandom:
    def __init__(self, seed):
        self.seed = seed
        self.cur = 0

    def get(self):
        self.cur = (self.cur + ((self.cur << 2) & MASK) + self.seed) & MASK
        return self.cur

    def reset(self):
        self.cur = 0


class TpScramble:
    A, B, C, D = 2111111 * 1000 + 111, 1492, 1776, 5115  # 2111111111
    def __init__(self, seed):
        self.st = [0] * 5
        h = seed if seed else MASK
        for i in range(5):
            h ^= (h << 13) & MASK
            h ^= h >> 17
            h ^= (h << 5) & MASK
            self.st[i] = h & MASK
        for _ in range(19):
            self.u32()

    def u32(self):
        v = (2111111111 * self.st[3] + 1492 * self.st[2] + 1776 * self.st[1]
             + 5115 * self.st[0] + self.st[4])
        self.st[3] = self.st[2]
        self.st[2] = self.st[1]
        self.st[1] = self.st[0]
        self.st[4] = (v >> 32) & MASK
        self.st[0] = v & MASK
        return self.st[0]

    def get_int(self, first, last):
        return first + int((self.u32() / 0x100000000) * (last - first + 1))


def random_sequence(count, seed):
    tp = TpScramble(seed)
    order = list(range(count))
    seq = [0] * count
    i = 0
    while len(order) > 1:
        n = tp.get_int(0, len(order) - 2)
        seq[order[n]] = i
        order.pop(n)
        i += 1
    seq[order[0]] = count - 1
    return seq


def reshuffle(data):
    chunk, seedraw = struct.unpack('<iI', data[:8])
    seed = seedraw ^ 0xF8EA
    body = data[8:]
    n = (len(body) - 1) // chunk + 1
    out = bytearray()
    for i in random_sequence(n, seed):
        p = i * chunk
        out += body[p:p + chunk]
    return bytes(out)


def pe_overlay(path):
    with open(path, 'rb') as f:
        d = f.read(0x1000)
        e = struct.unpack('<I', d[0x3C:0x40])[0]
        ns = struct.unpack('<H', d[e + 6:e + 8])[0]
        opt = struct.unpack('<H', d[e + 20:e + 22])[0]
        sec = e + 24 + opt
        end = 0
        for i in range(ns):
            s = d[sec + i * 40:sec + (i + 1) * 40]
            raw = struct.unpack('<I', s[20:24])[0]
            rsz = struct.unpack('<I', s[16:20])[0]
            end = max(end, raw + rsz)
        return end


def parse(path):
    base = pe_overlay(path)
    f = open(path, 'rb')
    f.seek(base)
    hdr = f.read(16)
    assert hdr[:4] == b'vff\0', hdr[:4]
    count = struct.unpack('<i', hdr[6:10])[0]
    rnd = TpRandom(0x75D6EE39)
    names = []
    off = base + 0xA
    for _ in range(count):
        f.seek(off)
        nl = struct.unpack('<I', f.read(4))[0]
        off += 4
        nb = bytearray(f.read(nl))
        for i in range(nl):
            nb[i] ^= rnd.get() & 0xFF
        names.append(nb.decode('cp932', 'replace'))
        off += nl
    rnd.reset()
    f.seek(off)
    offs = []
    for _ in range(count + 1):
        v = struct.unpack('<q', f.read(8))[0]
        offs.append(v ^ struct.unpack('<i', struct.pack('<I', rnd.get()))[0])
    offs = [base + o for o in offs]
    flags = f.read(count)
    ents = []
    for i in range(count):
        fl = flags[i]
        ents.append(dict(name=names[i], off=offs[i], size=offs[i + 1] - offs[i],
                         packed=(fl == 0 or fl == 3), scrambled=(fl == 2 or fl == 3), flags=fl))
    return base, ents


def read_entry(path, e):
    with open(path, 'rb') as f:
        f.seek(e['off'])
        d = f.read(e['size'])
    if e['scrambled']:
        if len(d) <= 8:
            return b''
        d = reshuffle(d)
    if e['packed']:
        d = zlib.decompress(d)
    return d


if __name__ == '__main__':
    if len(sys.argv) >= 4 and sys.argv[1] == '--extract':
        pat = sys.argv[2].lower()
        outdir = sys.argv[3]
        path = sys.argv[4]
        base, ents = parse(path)
        n = 0
        for e in ents:
            if not e['name'].lower().endswith(pat):
                continue
            p = os.path.join(outdir, e['name'].replace('\\', '/'))
            os.makedirs(os.path.dirname(p), exist_ok=True) if os.path.dirname(p) else None
            with open(p, 'wb') as f:
                f.write(read_entry(path, e))
            n += 1
        print('extracted', n, '->', outdir)
    else:
        path = sys.argv[-1]
        base, ents = parse(path)
        print('overlay', hex(base), 'entries', len(ents))
        for e in ents:
            print(f"{e['size']:>10} f{e['flags']} {e['name']}")
