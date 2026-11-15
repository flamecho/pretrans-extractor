#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[JP]♂ボ～イズ！！～イケメン陵辱パラダイス～  NPA 解包
Nitroplus NPA (NPA\x01)：
  索引名 key = key1*key2（乘积分支，名字解出即可读）
  内容前 0x1000+len(name) 字节：b[i] = KEY[b[i]] - key - i
  key = ((NameKey - sum(name)) * len(name) + arc_key) * unpackedSize & 0xFF, NameKey = 0x20101118
  本作 KeyTable 不在 GARbro 的 25 套 Order 里 —— 直接从 osu_trial.exe 偏移 1320464 处取（256B 置换），
  实测 17/17 条目唯一 zlib 命中且解压长度 == unpackedSize。
用法: python boiz_unpack.py <源目录> <输出目录>
"""
import struct, sys, os, zlib

NAMEKEY = 0x20101118
KEYTAB_OFF = 1320464


def load_key_table(exe_path):
    d = open(exe_path, 'rb').read()
    t = d[KEYTAB_OFF:KEYTAB_OFF + 256]
    assert len(set(t)) == 256, 'key table @%d not a permutation' % KEYTAB_OFF
    # exe 里存的是加密方向表，解密需其逆置换
    inv = bytearray(256)
    for i, v in enumerate(t):
        inv[v] = i
    return bytes(inv)


def decrypt_name(pos, curfile, arc_key):
    key = 0xFC * pos
    for sh in (0x18, 0x10, 0x08, 0):
        key -= arc_key >> sh
    for sh in (0x18, 0x10, 0x08, 0):
        key -= curfile >> sh
    return key & 0xFF


def open_npa(path, keytab):
    d = open(path, 'rb').read()
    assert d[:4] == b'NPA\x01', 'not NPA'
    key1 = struct.unpack_from('<i', d, 7)[0]
    key2 = struct.unpack_from('<i', d, 11)[0]
    compressed = d[15]
    encrypted = d[16]
    total = struct.unpack_from('<i', d, 17)[0]
    dirsize = struct.unpack_from('<I', d, 37)[0]
    arc = (key1 * key2) & 0xFFFFFFFF

    cur = 41
    out = {}
    for i in range(total):
        ns = struct.unpack_from('<i', d, cur)[0]
        raw = bytearray(d[cur + 4:cur + 4 + ns])
        for x in range(ns):
            raw[x] = (raw[x] + decrypt_name(x, i, arc)) & 0xFF
        info = cur + 5 + ns
        typ = d[cur + 4 + ns]
        fid, off, size, unp = struct.unpack_from('<IIII', d, info)
        cur += 4 + ns + 17
        if typ == 1:
            continue                      # 目录项
        name = bytes(raw).decode('cp932')
        base = dirsize + off + 41
        buf = bytearray(d[base:base + size])
        if encrypted:
            key = NAMEKEY
            for b in raw:
                key -= b
            key *= len(raw)
            key = (key + arc) & 0xFFFFFFFF
            key = (key * unp) & 0xFFFFFFFF
            key &= 0xFF
            n = min(0x1000 + len(raw), size)
            for k in range(n):
                buf[k] = (keytab[buf[k]] - key - k) & 0xFF
        data = bytes(buf)
        if compressed:
            data = zlib.decompress(data)
            assert len(data) == unp, '%s: unpacked %d != %d' % (name, len(data), unp)
        out[name] = data
    return out


def main():
    src = sys.argv[1]
    dst = sys.argv[2]
    keytab = load_key_table(os.path.join(src, 'osu_trial.exe'))
    os.makedirs(dst, exist_ok=True)
    n = 0
    for arcname in sorted(os.listdir(src)):
        if not arcname.lower().endswith('.npa'):
            continue
        files = open_npa(os.path.join(src, arcname), keytab)
        sub = os.path.join(dst, arcname[:-4])
        os.makedirs(sub, exist_ok=True)
        for name, data in files.items():
            path = os.path.join(sub, name.replace('\\', '/'))
            d = os.path.dirname(path)
            if d:
                os.makedirs(d, exist_ok=True)
            with open(path, 'wb') as fh:
                fh.write(data)
            n += 1
        print('%-12s %3d files' % (arcname, len(files)))
    print('total %d files -> %s' % (n, dst))


if __name__ == '__main__':
    main()
