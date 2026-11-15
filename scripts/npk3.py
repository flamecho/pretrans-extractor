# -*- coding: utf-8 -*-
"""NPK3 (Nitroplus Diesel Engine) unpacker.

Format (confirmed against marcussacana/MwareStuff NPK3Tool + live key dump):
  header 0x00: magic 'NPK3' | u32 minor | 16B IV | u32 count | u32 tableSize
  table  @0x20: AES-256-CBC(PKCS7, key, IV) of count records:
      u8 mode | u16 pathLen | path(UTF-8) | u32 fileSize | 32B sha256 |
      u32 segCount | segCount * {i64 offset, u32 alignedSize, u32 realSize,
                                 u32 decompressedSize}
  data: each segment is AES-256-CBC(key, IV) ciphertext of alignedSize bytes;
      if realSize < decompressedSize the plaintext is a zstd stream.

AES via Windows CNG (bcrypt); zstd via 7z.
"""
import argparse, ctypes, ctypes.wintypes as w, os, struct, subprocess, sys, tempfile

Z7 = r'C:\Program Files\7-Zip\7z.exe'
bcrypt = ctypes.WinDLL('bcrypt', use_last_error=True)
bcrypt.BCryptOpenAlgorithmProvider.argtypes = [ctypes.POINTER(ctypes.c_void_p), w.LPCWSTR, w.LPCWSTR, w.ULONG]
bcrypt.BCryptSetProperty.argtypes = [ctypes.c_void_p, w.LPCWSTR, ctypes.c_char_p, w.ULONG, w.ULONG]
bcrypt.BCryptGenerateSymmetricKey.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p,
                                             w.ULONG, ctypes.c_char_p, w.ULONG, w.ULONG]
bcrypt.BCryptDestroyKey.argtypes = [ctypes.c_void_p]
bcrypt.BCryptCloseAlgorithmProvider.argtypes = [ctypes.c_void_p, w.ULONG]
bcrypt.BCryptDecrypt.argtypes = [ctypes.c_void_p, ctypes.c_char_p, w.ULONG, ctypes.c_void_p, ctypes.c_char_p,
                                 w.ULONG, ctypes.c_char_p, w.ULONG, ctypes.POINTER(w.ULONG), w.ULONG]


class AES:
    def __init__(self, key):
        h = ctypes.c_void_p()
        if bcrypt.BCryptOpenAlgorithmProvider(ctypes.byref(h), 'AES', None, 0):
            raise OSError('BCryptOpenAlgorithmProvider failed')
        self.hAlg = h
        mode = 'ChainingModeCBC'.encode('utf-16-le') + b'\x00\x00'
        if bcrypt.BCryptSetProperty(h, 'ChainingMode', mode, len(mode), 0):
            raise OSError('BCryptSetProperty failed')
        hk = ctypes.c_void_p()
        if bcrypt.BCryptGenerateSymmetricKey(h, ctypes.byref(hk), None, 0, key, len(key), 0):
            raise OSError('BCryptGenerateSymmetricKey failed')
        self.hKey = hk

    def decrypt(self, data, iv):
        # BCryptDecrypt writes the chaining IV back into pbIV, so hand it a copy.
        ivbuf = ctypes.create_string_buffer(bytes(iv), len(iv))
        out = ctypes.create_string_buffer(len(data))
        got = w.ULONG(0)
        rc = bcrypt.BCryptDecrypt(self.hKey, data, len(data), None, ivbuf, len(iv), out, len(data),
                                  ctypes.byref(got), 0)
        if rc:
            raise OSError('BCryptDecrypt failed %d' % rc)
        return out.raw[:got.value]

    def close(self):
        bcrypt.BCryptDestroyKey(self.hKey)
        bcrypt.BCryptCloseAlgorithmProvider(self.hAlg, 0)


def zstd_decomp(data):
    with tempfile.NamedTemporaryFile(suffix='.zst', delete=False) as f:
        f.write(data)
        tmp = f.name
    try:
        r = subprocess.run([Z7, 'e', '-so', tmp], capture_output=True)
        if r.returncode:
            raise RuntimeError('7z zstd failed: ' + r.stderr.decode('oem', 'replace')[:200])
        return r.stdout
    finally:
        os.unlink(tmp)


def open_npk(path, key):
    d = open(path, 'rb').read()
    if d[:4] != b'NPK3':
        raise ValueError('not NPK3: ' + path)
    minor, = struct.unpack_from('<I', d, 4)
    iv = d[8:24]
    count, tsize = struct.unpack_from('<II', d, 24)
    if count * 40 > tsize + 64:
        raise ValueError('implausible table: count=%d size=%d' % (count, tsize))
    aes = AES(bytes.fromhex(key) if isinstance(key, str) else key)
    tbl = aes.decrypt(d[0x20:0x20 + tsize], iv)
    p = 0
    ents = []
    for _ in range(count):
        mode = tbl[p]
        plen, = struct.unpack_from('<H', tbl, p + 1)
        p += 3
        name = tbl[p:p + plen].decode('utf-8')
        p += plen
        fsize, = struct.unpack_from('<I', tbl, p)
        p += 4
        sha = tbl[p:p + 32]
        p += 32
        sc, = struct.unpack_from('<I', tbl, p)
        p += 4
        segs = []
        for _s in range(sc):
            off, al, rs, ds = struct.unpack_from('<qIII', tbl, p)
            p += 20
            segs.append((off, al, rs, ds))
        ents.append({'mode': mode, 'name': name, 'size': fsize, 'sha': sha, 'segs': segs})
    return {'data': d, 'iv': iv, 'aes': aes, 'entries': ents, 'minor': minor}


def read_entry(npk, e):
    out = bytearray()
    for off, al, rs, ds in e['segs']:
        plain = npk['aes'].decrypt(npk['data'][off:off + al], npk['iv'])
        seg = plain[:rs]
        if rs < ds:
            seg = zstd_decomp(seg)
            if len(seg) != ds:
                raise RuntimeError('size mismatch %s: %d != %d' % (e['name'], len(seg), ds))
        out += seg
    return bytes(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('npk')
    ap.add_argument('outdir')
    ap.add_argument('--key', required=True)
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--only', default=None, help='substring filter')
    a = ap.parse_args()
    npk = open_npk(a.npk, a.key)
    print('entries', len(npk['entries']), 'minor', npk['minor'], file=sys.stderr)
    os.makedirs(a.outdir, exist_ok=True)
    n = 0
    bad = 0
    for e in npk['entries']:
        if a.only and a.only not in e['name']:
            continue
        if a.list:
            print('%10d %s' % (e['size'], e['name']))
            continue
        data = read_entry(npk, e)
        if len(data) != e['size']:
            print('SIZE MISMATCH', e['name'], len(data), e['size'], file=sys.stderr)
        import hashlib
        if hashlib.sha256(data).digest() != e['sha']:
            print('SHA MISMATCH', e['name'], file=sys.stderr)
            bad += 1
        dst = os.path.join(a.outdir, e['name'].replace('\\', '/'))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, 'wb') as f:
            f.write(data)
        n += 1
    if not a.list:
        print('wrote', n, 'files, sha mismatches', bad, '->', a.outdir, file=sys.stderr)


if __name__ == '__main__':
    main()
