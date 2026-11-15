#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ALTOR（PC / KiriKiri XP3 + KAGeXpress 3.0）一步出成品。

用法:
    python scripts/altor_extract.py --src "<解包后的 Altor_jp_ver1.00.exe>" \
        --out os.path.join(VNTRANS_HOME, "提取结果/[JP]ALTOR.txt") [--dump <解包目录>]

阶段:
    1) XP3 索引（BASE=0x321000，u64@BASE+0x0B 相对 BASE，zlib@BASE+idx+17）
    2) 全量解密（整文件单字节 XOR；key 判据链：魔数 → UTF-16LE → cp932 平文 → cp932 严格解码率）
    3) 成行（KAG 框界：两次 [CM] 之间；[r] 不是显示换行 ⇒ 同框拼接；message3=名字窗剔除）

判据出处见解析报告 §3~§5 与 skill `engines/kirikiri.md` 第六变体。
"""
import argparse
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import struct
import sys
import zlib

BASE = 0x321000

# 6 个小体积 CP932 脚本（首字符只能是 ';' '@' '[' '*' '/' 或换行 ⇒ 反推 key，已肉眼确认头部）
OVERRIDE = {
    'scenario/autolabel.ks':       0x0E,
    'scenario/autoInsertLabel.ks': 0xC3,
    'scenario/func.ks':            0x96,
    'scenario/textset.ks':         0x74,
    'scenario/staff.ks':           0x1C,
    'scenario/staffroll.ks':       0xF8,
}

MAGIC = {
    '.png': b'\x89PNG\r\n\x1a\n', '.jpg': b'\xff\xd8\xff', '.ogg': b'OggS',
    '.wav': b'RIFF', '.wmv': b'\x30\x26\xb2\x75\x8e\x66\xcf\x11',
}

TOKENS = ['storage=', 'layer=', 'time=', '@image', '[eval', 'exp=', 'visible',
          'opacity', 'function', 'var ', 'class ', '@if', '[p]', '@current',
          'margin', 'message', '[cm]', '@bg', 'left=', 'top=']

FILES = ['first.ks', '59.ks', '69.ks']          # 序章/共通 → 獄寺ルート → 骸ルート
TAG = re.compile(r'\[[^\]\n]*\]')
CUR = re.compile(r'@current\s+layer\s*=\s*(\w+)')
BOUND = re.compile(r'\[(?:cm|plc|p|l|s)\]', re.I)


def xor(bs, k):
    return bytes(b ^ k for b in bs)


def ascii_ratio(bs):
    n = len(bs) // 2
    if n < 8:
        return 0.0
    n = min(n, 6000)
    c = 0
    for i in range(n):
        u = bs[2 * i] | (bs[2 * i + 1] << 8)
        if u < 0x80 and (0x20 <= u or u in (0x09, 0x0a, 0x0d)):
            c += 1
    return c / n


def token_hits(bs):
    tl = bs[:12000].decode('utf-16-le', 'replace').lower()
    return sum(1 for k in TOKENS if k in tl)


def cp932_ratio(bs):
    t = bs[:8192].decode('cp932', 'replace')
    return 1.0 - t.count('\ufffd') / max(1, len(t))


def guess_key(bs, ext):
    """顺序不可换：魔数 → UTF-16LE → 明平文 → cp932。"""
    mg = MAGIC.get(ext)
    if mg and len(bs) >= len(mg):
        k = bs[0] ^ mg[0]
        if all(bs[i] ^ mg[i] == k for i in range(len(mg))):
            return k, 'magic'
    cand = max(((ascii_ratio(xor(bs[:12000], k)), k) for k in range(256)))
    if cand[0] >= 0.30 and token_hits(xor(bs[:12000], cand[1])) >= 1:
        return cand[1], 'u16:%.3f' % cand[0]
    if cp932_ratio(bs) > 0.995 and bs[:1] not in (b'\x89', b'\xff', b'O', b'R', b'\x30'):
        return 0, 'plain'
    cand = max(((cp932_ratio(xor(bs[:12000], k)), k) for k in range(256)))
    return cand[1], 'sjis:%.3f' % cand[0]


def read_xp3(src):
    """返回 [(name, decrypted_bytes, key, how)]，按索引顺序。"""
    d = open(src, 'rb').read()
    if d[BASE:BASE + 11] != b'XP3\r\n \n\x1a\x8bg\x01':
        sys.exit('XP3 头不在 0x%X —— 请确认入参是 Altor_jp_ver1.00.exe' % BASE)
    q = BASE + struct.unpack_from('<Q', d, BASE + 11)[0] + 17
    out = zlib.decompressobj().decompress(d[q:])
    p, rows = 0, []
    while p + 12 <= len(out):
        if out[p:p + 4] != b'File':
            break
        size = struct.unpack_from('<Q', out, p + 4)[0]
        pay = out[p + 12:p + 12 + size]
        r, name, segs = 0, None, []
        while r + 12 <= len(pay):
            t2 = pay[r:r + 4]
            s2 = struct.unpack_from('<Q', pay, r + 4)[0]
            sp = pay[r + 12:r + 12 + s2]
            if t2 == b'info':
                nlen = struct.unpack_from('<H', sp, 20)[0]
                name = sp[22:22 + nlen * 2].decode('utf-16-le', 'replace')
            elif t2 == b'segm':
                for i in range(0, len(sp) - 27, 28):
                    _, off, org, comp = struct.unpack_from('<IQQQ', sp, i)
                    segs.append((off, org, comp))
            r += 12 + s2
        p += 12 + size
        if not name:
            continue
        buf = bytearray()
        for off, org, comp in segs:
            raw = d[BASE + off:BASE + off + comp]          # off 相对 BASE
            buf += zlib.decompress(raw) if comp != org else raw
        bs = bytes(buf)
        ext = os.path.splitext(name)[1].lower()
        if not bs:
            rows.append((name, bs, None, 'empty'))
            continue
        k = OVERRIDE.get(name)
        how = 'override'
        if k is None:
            k, how = guess_key(bs, ext)
        rows.append((name, xor(bs, k), k, how))
    return d, rows


def decode_script(bs):
    if bs[:2] == b'\xff\xfe':
        t = bs[2:].decode('utf-16-le', 'replace')
    else:
        t = bs.decode('cp932', 'replace')
    # 行尾三种混用：CRLF / 裸 CR（first.ks 全裸 CR）/ 裸 LF
    return t.replace('\r\n', '\n').replace('\r', '\n')


def do_lines(files):
    out = []
    for fn in FILES:
        if fn not in files:
            continue
        layer, buf = None, []
        for L in decode_script(files[fn]).split('\n'):
            m = CUR.search(L)
            if m:
                layer = m.group(1)
            s = L.strip()
            if s and s[0] not in ';@*' and not s.startswith('//'):
                b = TAG.sub('', s)
                if b.strip() and layer == 'message1':      # message3 = 名字窗，剔除
                    buf.append(b)
            if BOUND.search(L):
                if buf:
                    line = ''.join(buf).strip(' \t')
                    if line:
                        out.append(line)
                    buf = []
        if buf:
            line = ''.join(buf).strip(' \t')
            if line:
                out.append(line)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True, help='解包后的 Altor_jp_ver1.00.exe')
    ap.add_argument('--out', required=True, help='成品 txt 路径')
    ap.add_argument('--dump', help='可选：把 826 个解密文件写到该目录')
    a = ap.parse_args()

    d, rows = read_xp3(a.src)
    print('XP3 条目 %d' % len(rows))

    files = {}
    for name, dec, k, how in rows:
        if a.dump and dec:
            dst = os.path.join(a.dump, name.replace('/', os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if len(os.path.basename(dst)) > 180:
                dst = dst[:150] + '~long' + os.path.splitext(name)[1]
            open(dst, 'wb').write(dec)
        if name.startswith('scenario/') and name.endswith('.ks'):
            files[os.path.basename(name)] = dec

    lines = do_lines(files)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    data = '\n'.join(lines) + '\n'
    with open(a.out, 'wb') as fh:
        fh.write(b'\xef\xbb\xbf' + data.encode('utf-8'))
    print('成品 %s  行 %d  字 %d' % (a.out, len(lines), len(data)))


if __name__ == '__main__':
    main()
