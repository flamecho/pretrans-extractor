#!/usr/bin/env python3
"""btf_mdf.py —— M2 PSB 的 MDF(MT19937) 外壳解密（PSP 版 Kaleido/ADVENGINE）。

算法（FreeMote PsbExtension.EncodeMdf / CreateMdfRandom）：
  seed  = key + fileName(UTF-8)
  seeds = MD5(seed) 的 4 个 u32(LE)
  mt    = MT19937 ar, init_by_array(seeds)
  keybuf= 连续 GenerateUInt32() 拼成 LE 字节流，长度 = keyLength（本作 131）
  plain = data[:8] + (data[8:] XOR keybuf[i % keyLength])
  然后 zlib 解压 → PSB

用法: python scripts/btf_mdf.py <file.psb.m> <key> <out.psb> [keylen]
"""
import sys, zlib, hashlib, struct

class MT19937:
    N, M = 624, 397
    MATRIX_A = 0x9908b0df
    UPPER = 0x80000000
    LOWER = 0x7fffffff

    def __init__(self):
        self.mt = [0] * self.N
        self.idx = self.N + 1

    def init_genrand(self, s):
        self.mt[0] = s & 0xffffffff
        for i in range(1, self.N):
            self.mt[i] = (1812433253 * (self.mt[i-1] ^ (self.mt[i-1] >> 30)) + i) & 0xffffffff
        self.idx = self.N

    def init_by_array(self, key):
        self.init_genrand(19650218)
        i, j = 1, 0
        k = max(self.N, len(key))
        for _ in range(k):
            self.mt[i] = ((self.mt[i] ^ ((self.mt[i-1] ^ (self.mt[i-1] >> 30)) * 1664525)) + key[j] + j) & 0xffffffff
            i += 1; j += 1
            if i >= self.N:
                self.mt[0] = self.mt[self.N-1]; i = 1
            if j >= len(key):
                j = 0
        for _ in range(self.N - 1):
            self.mt[i] = ((self.mt[i] ^ ((self.mt[i-1] ^ (self.mt[i-1] >> 30)) * 1566083941)) - i) & 0xffffffff
            i += 1
            if i >= self.N:
                self.mt[0] = self.mt[self.N-1]; i = 1
        self.mt[0] = 0x80000000
        self.idx = self.N

    def _gen(self):
        if self.idx >= self.N:
            for kk in range(self.N):
                y = (self.mt[kk] & self.UPPER) | (self.mt[(kk+1) % self.N] & self.LOWER)
                self.mt[kk] = self.mt[(kk + self.M) % self.N] ^ (y >> 1) ^ (self.MATRIX_A if y & 1 else 0)
            self.idx = 0
        y = self.mt[self.idx]; self.idx += 1
        y ^= y >> 11
        y ^= (y << 7) & 0x9d2c5680
        y ^= (y << 15) & 0xefc60000
        y ^= y >> 18
        return y & 0xffffffff

    def uint32(self):
        return self._gen()


def keystream(key, filename, keylen):
    seed = (key + filename).encode('utf-8')
    h = hashlib.md5(seed).digest()
    words = list(struct.unpack('<4I', h))
    mt = MT19937(); mt.init_by_array(words)
    n = (keylen // 4 + 1) * 4
    buf = bytearray()
    while len(buf) < n:
        buf += struct.pack('<I', mt.uint32())
    return bytes(buf[:keylen])


def mdf_decrypt(data, key, filename, keylen=131):
    ks = keystream(key, filename, keylen)
    out = bytearray(data[:8])
    payload = data[8:]
    L = len(ks)
    # 4096 周期的 RAM 表加速
    for i in range(len(payload)):
        out.append(payload[i] ^ ks[i % L])
    plain = zlib.decompress(bytes(out[8:]))
    return plain


if __name__ == '__main__':
    src, key, dst = sys.argv[1], sys.argv[2], sys.argv[3]
    keylen = int(sys.argv[4]) if len(sys.argv) > 4 else 131
    import os
    fn = os.path.basename(src)
    data = open(src, 'rb').read()
    plain = mdf_decrypt(data, key, fn, keylen)
    open(dst, 'wb').write(plain)
    print('%s -> %s  %d bytes  head=%r' % (fn, dst, len(plain), plain[:8]))
