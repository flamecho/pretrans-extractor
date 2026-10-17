#!/usr/bin/env python3
"""btf_pgd.py —— PSP PGD（\\0PGD / drm_type=1 / mac_type=1）解密。

算法来源：tpunix/kirk_engine  npdrm/dnas.c + kirk/amctrl.c + kirk/kirk_engine.c
  · BBMac(type1) = AES-CMAC(key=kirk7_key38) 再 ^ loc_1CD4；带 vkey 时再 AES_enc 一次
  · 内容解密 = CTR 变体（amctrl sub_428 / sub_1F8）：
        nonce      = AES_dec(k39, key ^ loc_1CF4) ^ loc_1CE4      （12 字节 nonce + u32 计数）
        ks_block i = AES_dec(k63, N||LE(1+i)) ^ (N||LE(i))        （i=0 时前项取 0×16）
  kirk 表内密钥 0x38 / 0x39 / 0x63 均为公开值。

用法:
  python scripts/btf_pgd.py check   <pgd>
  python scripts/btf_pgd.py decrypt <pgd> <out> [off size]   # off/size 相对解密后数据起点
"""
import struct, sys
from Crypto.Cipher import AES

KEY38 = bytes([0x12,0x46,0x8D,0x7E,0x1C,0x42,0x20,0x9B,0xBA,0x54,0x26,0x83,0x5E,0xB0,0x33,0x03])
KEY39 = bytes([0xC4,0x3B,0xB6,0xD6,0x53,0xEE,0x67,0x49,0x3E,0xA9,0x5F,0xBC,0x0C,0xED,0x6F,0x8A])
KEY63 = bytes([0x9C,0x9B,0x13,0x72,0xF8,0xC6,0x40,0xCF,0x1C,0x62,0xF5,0xD5,0x92,0xDD,0xB5,0x82])
KEY1A90 = bytes([0xED,0xE2,0x5D,0x2D,0xBB,0xF8,0x12,0xE5,0x3C,0x5C,0x59,0x32,0xFA,0xE3,0xE2,0x43])
LOC_1CD4 = bytes([0xE3,0x50,0xED,0x1D,0x91,0x0A,0x1F,0xD0,0x29,0xBB,0x1C,0x3E,0xF3,0x40,0x77,0xFB])
LOC_1CE4 = bytes([0x13,0x5F,0xA4,0x7C,0xAB,0x39,0x5B,0xA4,0x76,0xB8,0xCC,0xA9,0x8F,0x3A,0x04,0x45])
LOC_1CF4 = bytes([0x67,0x8D,0x7F,0xA3,0x2A,0x9C,0xA0,0xD1,0x50,0x8A,0xD8,0x38,0x5E,0x4B,0x01,0x7E])
ZERO16 = b'\x00' * 16


def _xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


def aes_cbc_dec(key, data):
    return AES.new(key, AES.MODE_CBC, ZERO16).decrypt(data)


def aes_cbc_enc(key, data):
    return AES.new(key, AES.MODE_CBC, ZERO16).encrypt(data)


def aes_enc_block(key, blk):
    return AES.new(key, AES.MODE_ECB).encrypt(blk)


class BBMac:
    def __init__(self):
        self.key = b''
        self.pad = b''
        self.pad_size = 0

    def update(self, data):
        buf = self.pad + data
        if len(buf) < 16:
            self.pad = buf
            self.pad_size = len(buf)
            return
        self.pad_size = (len(buf) % 16) or 16
        n = len(buf) - self.pad_size
        self.pad = buf[n:]
        if n == 0:
            return
        body = buf[:n]
        head = _xor(body[:16], self.key) if self.key else body[:16]
        out = aes_cbc_enc(KEY38, head + body[16:])
        self.key = out[-16:]

    @staticmethod
    def _shl(t):
        out = bytearray(16)
        carry = 0x87 if (t[0] & 0x80) else 0
        for i in range(15):
            out[i] = ((t[i] << 1) | (t[i + 1] >> 7)) & 0xFF
        out[15] = ((t[15] << 1) ^ carry) & 0xFF
        return bytes(out)

    def _final_block(self):
        t = self._shl(aes_enc_block(KEY38, ZERO16))
        if self.pad_size < 16:
            t = self._shl(t)
            pad = self.pad + b'\x80' + b'\x00' * (15 - self.pad_size)
        else:
            pad = self.pad
        return _xor(pad, t)

    def final(self, vkey=None):
        blk = self._final_block()
        c = aes_enc_block(KEY38, _xor(blk, self.key))
        mac = _xor(c, LOC_1CD4)
        if vkey:
            mac = aes_enc_block(KEY38, _xor(mac, vkey))
        return mac


def mac_of(data, vkey=None):
    m = BBMac()
    m.update(data)
    return m.final(vkey)


def getkey(protected_mac, data_mac):
    return _xor(data_mac, aes_cbc_dec(KEY38, protected_mac))


def _nonce(keymat):
    return _xor(aes_cbc_dec(KEY39, _xor(keymat, LOC_1CF4)), LOC_1CE4)


def cipher_stream(keymat, off, size):
    """amctrl sub_428/sub_1F8 等价；off/size 需 16 对齐，off 以字节计（seed = 1 + off/16）。"""
    if off % 16 or size % 16:
        raise ValueError('need 16-aligned')
    nonce = _nonce(keymat)
    n = size // 16
    prefix = nonce[:12]
    counters = bytearray(n * 16)
    for i in range(n):
        struct.pack_into('<I', counters, i * 16 + 12, 1 + off // 16 + i)
        counters[i * 16:i * 16 + 12] = prefix
    ks = bytearray(aes_cbc_dec(KEY63, bytes(counters)))
    if off:
        # CBC 链首块的前项＝全局块号 off/16 的计数块（block 0 时前项为 0，无需处理）
        prev0 = prefix + struct.pack('<I', off // 16)
        ks[0:16] = _xor(bytes(ks[0:16]), prev0)
    return bytes(ks)


def header_desc(pgd):
    assert pgd[:4] == b'\x00PGD', pgd[:4]
    key_index, drm_type = struct.unpack_from('<II', pgd, 4)
    ok80 = mac_of(pgd[0:0x80], KEY1A90) == pgd[0x80:0x90]
    vkey = getkey(pgd[0x70:0x80], mac_of(pgd[0:0x70]))
    ckey = _xor(pgd[0x10:0x20], vkey)
    desc = _xor(pgd[0x30:0x90], cipher_stream(ckey, 0, 0x60))
    full = pgd[:0x30] + desc
    file_size, block_size, data_offset = struct.unpack_from('<III', full, 0x44)
    return dict(key_index=key_index, drm_type=drm_type, mac80=ok80, vkey=vkey,
                file_size=file_size, block_size=block_size,
                data_offset=data_offset, dkey=full[0x30:0x40])


def decrypt_range(pgd, off, size, h=None):
    h = h or header_desc(pgd)
    keymat = _xor(h['dkey'], h['vkey'])
    pad = off % 16
    b0 = off - pad
    need = ((size + pad + 15) // 16) * 16
    ks = cipher_stream(keymat, b0, need)[pad:pad + size]
    chunk = pgd[0x90 + off:0x90 + off + size]
    return _xor(chunk, ks), h


def main():
    cmd = sys.argv[1]
    pgd = open(sys.argv[2], 'rb').read()
    if cmd == 'check':
        h = header_desc(pgd)
        for k in ('key_index', 'drm_type', 'mac80', 'file_size', 'block_size', 'data_offset'):
            print('%-12s %s' % (k, h[k]))
        print('vkey        ', h['vkey'].hex())
        print('pgd size', len(pgd))
        d, _ = decrypt_range(pgd, 0, 64, h)
        print('data[0:16]  ', d[:16].hex(' '), ' mdf?', d[:4] == b'mdf\x00')
    elif cmd == 'decrypt':
        h0 = header_desc(pgd)
        if len(sys.argv) > 4:
            off, size = int(sys.argv[4]), int(sys.argv[5])
            d, _ = decrypt_range(pgd, off, size, h0)
        else:
            size = (h0['file_size'] + 15) & ~15
            d, _ = decrypt_range(pgd, 0, size, h0)
            d = d[:h0['file_size']]
        open(sys.argv[3], 'wb').write(d)
        print('wrote', sys.argv[3], len(d))


if __name__ == '__main__':
    main()
