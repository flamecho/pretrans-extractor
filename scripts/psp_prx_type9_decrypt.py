#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PSP ~PSP (EncryptType 9) EBOOT.BIN decrypter.
Faithful port of PPSSPP Core/ELF/PrxDecrypter.cpp::pspDecryptType9 + libkirk kirk_CMD1/kirk7.
Keys are public (PSARDUMPER/JPCSP).  IV is always all-zero.
Usage: python decrypt_eboot.py <EBOOT.BIN> <out.bin>
"""
import sys, re, struct, hashlib, gzip
from Crypto.Cipher import AES

Z16 = b'\0' * 16
KIRK1 = bytes([0x98, 0xC9, 0x40, 0x97, 0x5C, 0x1D, 0x10, 0xE8,
               0x7F, 0xE6, 0x0E, 0xA3, 0xFD, 0x03, 0xA8, 0xBA])
TAG2 = {
    0xD91613F0: (bytes([0xEB, 0xFF, 0x40, 0xD8, 0xB4, 0x1A, 0xE1, 0x66,
                        0x91, 0x3B, 0x8F, 0x64, 0xB6, 0xFC, 0xB7, 0x12]), 0x5D),
}
KV = []          # keyvault, filled from kirk_engine.c


def load_keyvault(path):
    src = open(path, encoding='utf-8').read()
    m = re.search(r'keyvault\[0x80\]\[0x10\]\s*=\s*\{(.*?)\n\};', src, re.S)
    rows = re.findall(r'\{([^}]*)\}', m.group(1))
    kv = [bytes(int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]{2}', r)) for r in rows]
    assert len(kv) == 0x80
    return kv


def aes_cbc_dec(key, data):
    assert len(data) % 16 == 0, len(data)
    return AES.new(key, AES.MODE_CBC, Z16).decrypt(data)


def kirk7(data, keyid):            # KIRK cmd4/7: AES-128-CBC decrypt, keyvault[keyid]
    return aes_cbc_dec(KV[keyid], data)


def expand_seed(seed, key):        # 0x90-byte xor stream
    buf = bytearray()
    for i in range(0, 0x90, 0x10):
        blk = bytearray(seed)
        blk[0] = i // 0x10
        buf += blk
    return bytearray(kirk7(bytes(buf), key))


def decrypt_type9(prx):
    tag = struct.unpack_from('<I', prx, 0xD0)[0]
    if tag not in TAG2:
        return None, 'unknown tag %08X' % tag
    seed, code = TAG2[tag]
    if any(b for b in prx[0xD4:0x104]):
        return None, 'nonzero 0xD4..0x104 (not type9)'

    xorbuf = expand_seed(seed, code)

    id_ = prx[0x140:0x150]
    kh = prx[0x80:0xB0] + prx[0xC0:0xD0]        # kirkHeader (raw, 0x40)
    km = prx[0xB0:0xC0]                          # kirkMetadata (0x10)
    ph = prx[0x00:0x80]                          # prxHeader

    # --- PRXType9::decrypt -> kirk7(id, id, 0x60) over contiguous [id|sha1|kh[0:0x3C]] ---
    contig = (id_ + prx[0x12C:0x140] + kh)[:0x60]
    d = bytearray(kirk7(contig, code))
    id_d = bytes(d[0x00:0x10])
    sha_d = bytes(d[0x10:0x24])
    kh_d = bytes(d[0x24:0x60]) + bytes(kh[0x3C:0x40])      # decrypted kirkHeader (0x40)

    # --- self check (pspDecryptType9 SHA1, compared against the decrypted sha1 field) ---
    h = hashlib.sha1()
    h.update(prx[0xD0:0xD4]); h.update(bytes(xorbuf[0:0x10])); h.update(b'\0' * 0x58)
    h.update(id_d); h.update(kh_d); h.update(km); h.update(ph)
    sha_ok = (h.digest() == sha_d)

    # --- build KIRK CMD1 header at out[0x40:0xD0] ---
    out = bytearray(prx)
    out[0x40:0xD0] = b'\0' * 0x90
    out[0xB0:0xC0] = km
    out[0xD0:0x150] = ph
    tmp = bytearray(0x40)                        # input = DECRYPTED kirkHeader
    for i in range(0x40):
        tmp[i] = kh_d[i] ^ xorbuf[0x10 + i]
    tmp = bytearray(kirk7(bytes(tmp), code))
    for i in range(0x40):
        tmp[i] ^= xorbuf[0x10 + 0x40 + i]
    out[0x40:0x80] = tmp
    out[0xA0] = 1                                # header->mode = KIRK_MODE_CMD1
    out[0xA1] = 0                                # header->ecdsa_hash = 0

    data_size = struct.unpack_from('<I', out, 0xB0)[0]
    data_offset = struct.unpack_from('<I', out, 0xB4)[0]

    # --- kirk_CMD1: session key = AES-CBC-dec(kirk1) of header[0:32] ---
    keys = aes_cbc_dec(KIRK1, bytes(out[0x40:0x60]))
    aes_key = keys[0:16]

    off = 0x40 + 0x90 + data_offset
    n = (data_size // 16) * 16
    plain = bytearray(aes_cbc_dec(aes_key, bytes(out[off:off + n])))
    if data_size % 16:
        plain += bytes(out[off + n: off + data_size])
    plain = bytes(plain[:data_size])

    info = dict(tag=tag, code=code, data_size=data_size, data_offset=data_offset,
                aes_key=aes_key.hex(), cmac_key=keys[16:32].hex(), sha_ok=sha_ok,
                head=plain[:16].hex())
    return plain, info


def main():
    global KV
    KV = load_keyvault(__file__.rsplit('/', 1)[0].rsplit('\\', 1)[0] + '/kirk_engine.c')
    plain, info = decrypt_type9(open(sys.argv[1], 'rb').read())
    if plain is None:
        print('FAIL:', info); return
    open(sys.argv[2], 'wb').write(plain)
    print('OK  wrote %s (%d bytes)' % (sys.argv[2], len(plain)))
    for k, v in info.items():
        print('   %-11s %s' % (k, v))
    if plain[:4] == b'\x1f\x8b\x08':
        g = gzip.decompress(plain)
        open(sys.argv[2] + '.gunzip', 'wb').write(g)
        print('   gunzip    -> %d bytes, head=%s' % (len(g), g[:8].hex()))


if __name__ == '__main__':
    main()
