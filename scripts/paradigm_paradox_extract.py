#!/usr/bin/env python3
"""Paradigm Paradox (Regista advGame engine) 全文本提取器 —— 定稿。

用法:
    python paradigm_paradox_extract.py <Paradigm Paradox.xci> <out_dir>

流程:
    XCI 卡带分区(明文) -> Program NCA
      · NCA3 头部：AES-XTS(header_key, Nintendo 大端 sector tweak)
      · 段数据：AES-CTR(title key = key_area slot2)
      · sec1 RomFS -> scr.pack
    scr.pack：自研 PRNG 流密码(XOR)，密钥字符串 "regista"
    解密后：[u32 count][count×{u32 size,u32 aux}]+脚本字节码
    字节码：AB <u16> <UTF-8> 00 = 一行；47 0D 00 <UTF-8> 00 = 说话人名
    一次点击 = 紧邻 AB 记录序列，其各行合并为一行。

依赖: pycryptodome（仅 AES 原语）。
"""
import os, re, struct, sys

from Crypto.Cipher import AES

M64 = (1 << 64) - 1
PRNG_M = 0x6C078965
KEY_STR = b'regista\x00'
HEROINE_NAME = 'ユウキ'
MASK64 = (1 << 64) - 1


# ---------------------------------------------------------------- NCA / XCI
def nca_xts(key: bytes, data: bytes, sector_size=0x200, start_sector=0) -> bytes:
    """Nintendo NCA AES-XTS: 大端 sector tweak。"""
    e1 = AES.new(key[:16], AES.MODE_ECB)
    e2 = AES.new(key[16:32], AES.MODE_ECB)

    def mul(x):
        c = x[15] >> 7
        x = bytearray(((int.from_bytes(x, 'little') << 1) & ((1 << 128) - 1)).to_bytes(16, 'little'))
        if c:
            x[0] ^= 0x87
        return bytes(x)

    out = bytearray()
    for si in range(len(data) // sector_size):
        sec = data[si * sector_size:(si + 1) * sector_size]
        tw = e2.encrypt((start_sector + si).to_bytes(16, 'big'))
        for bi in range(0, sector_size, 16):
            b = sec[bi:bi + 16]
            out += bytes(a ^ b for a, b in zip(e1.decrypt(bytes(a ^ c for a, c in zip(b, tw))), tw))
            tw = mul(tw)
    return bytes(out)


def aes_ctr(key, ctr_block, data):
    aes = AES.new(key, AES.MODE_ECB)
    base = int.from_bytes(ctr_block, 'big')
    out = bytearray()
    for i in range(0, len(data), 16):
        ks = aes.encrypt(((base + i // 16) & ((1 << 128) - 1)).to_bytes(16, 'big'))
        out += bytes(a ^ b for a, b in zip(data[i:i + 16], ks))
    return bytes(out)


def load_keys(path):
    ks = {}
    for line in open(path, encoding='utf-8', errors='replace'):
        line = line.strip()
        if line and '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            ks[k.strip()] = v.strip()
    return ks


def read_hfs0(f, off, base=None):
    f.seek(off)
    hdr = f.read(0x10)
    n, strsz = struct.unpack('<II', hdr[4:12])
    ents = []
    for _ in range(n):
        e = f.read(0x40)
        o, s, so = struct.unpack('<QQI', e[:20])
        ents.append((o, s, so))
    strtab = f.read(strsz)
    names = []
    for o, s, so in ents:
        names.append(strtab[so:strtab.index(b'\0', so)].decode())
    return names, ents, off + 0x10 + n * 0x40 + strsz


def decrypt_scr_pack(data: bytes) -> bytes:
    seed = 0x72
    for b in KEY_STR[1:]:
        if b == 0:
            break
        seed = (seed + b) & 0xFFFFFFFF
    x8 = seed & M64
    x8 ^= x8 >> 30
    x13 = (x8 * PRNG_M) & M64
    x8 = (x13 ^ (x13 >> 30)) * PRNG_M + 1 & M64
    x9 = x8
    x8 = (x8 ^ (x8 >> 30)) * PRNG_M + 2 & M64
    x10 = x8 ^ (x8 >> 30)
    x10 = (x10 * PRNG_M + 3) & M64
    out = bytearray()
    for _ in range(len(data)):
        x13 ^= (x13 << 11) & M64
        x13 ^= x13 >> 8
        x0 = x9
        x9 = x8
        x8 = x10
        x10 = (x13 ^ x10) ^ (x8 >> 19)
        out.append(x10 & 0xFF)
        x13 = x0
    return bytes(a ^ b for a, b in zip(data, out))


# ---------------------------------------------------------------- text
RUBY = re.compile(r'%R([^%]*)%R(\d+)')


def decode_inline(s: str) -> str:
    out, i = [], 0
    while True:
        m = RUBY.search(s, i)
        if not m:
            out.append(s[i:])
            break
        out.append(s[i:m.start()])
        n = int(m.group(2))
        out.append(s[m.end():m.end() + n])
        i = m.end() + n
    s = ''.join(out).replace('%N', '').replace('%h1', HEROINE_NAME)
    return s


BOX_RE = re.compile(rb'\xab..([^\x00]*)\x00')


def extract_lines(dec: bytes):
    recs = []
    for m in BOX_RE.finditer(dec):
        try:
            s = m.group(1).decode('utf-8')
        except UnicodeDecodeError:
            continue
        if not any(('\u3040' <= c <= '\u30ff') or ('\u4e00' <= c <= '\u9fff') or
                   ('\uff01' <= c <= '\uff60') or c in '「」、。…―' for c in s):
            continue
        recs.append((m.start(), m.end(), s))
    lines, cur, prev = [], [], None
    for st, en, s in recs:
        if prev is not None and st != prev:
            lines.append(cur)
            cur = []
        cur.append(s)
        prev = en
    if cur:
        lines.append(cur)
    out = []
    for parts in lines:
        t = decode_inline(''.join(parts))
        if out and out[-1] == t:
            continue
        out.append(t)
    return out


def main():
    xci, outdir = sys.argv[1], sys.argv[2]
    keys = load_keys(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '_sw', 'prod.keys'))
    f = open(xci, 'rb')
    # root HFS0
    f.seek(0x100 + 0x30)
    hfs0_off = struct.unpack('<Q', f.read(8))[0]
    names, ents, base = read_hfs0(f, hfs0_off)
    sec = [e for n, e in zip(names, ents) if n == 'secure'][0]
    sbase = base + sec[0]
    snames, sents, sbase2 = read_hfs0(f, sbase)
    prog_off = sbase2 + sents[0][0]
    prog_size = sents[0][1]

    # NCA header
    f.seek(prog_off)
    hdr = nca_xts(bytes.fromhex(keys['header_key']), f.read(0xC00))
    kg = max(hdr[0x206], hdr[0x220]) - 1
    dk = AES.new(bytes.fromhex(keys[f'key_area_key_application_{kg:02x}']), AES.MODE_ECB).decrypt(hdr[0x300:0x340])
    titlekey = dk[0x20:0x30]
    sections = [struct.unpack('<II', hdr[0x240 + i * 0x10:0x248 + i * 0x10]) for i in range(4)]
    ctrs = [hdr[0x400 + i * 0x200 + 0x140:0x400 + i * 0x200 + 0x148] for i in range(4)]

    def read_section(i, off, ln):
        ms = sections[i][0] << 9
        pos = ms + off
        aligned = pos & ~0xF
        delta = pos - aligned
        f.seek(prog_off + aligned)
        ct = f.read(delta + ln)
        ctr = bytearray(16)
        for j in range(8):
            ctr[j] = ctrs[i][7 - j]
        v = aligned >> 4
        for j in range(8):
            ctr[15 - j] = v & 0xFF
            v >>= 8
        return aes_ctr(titlekey, bytes(ctr), ct)[delta:delta + ln]

    # RomFS header
    rom = 0x1C000 + 0xB3C000
    rh = struct.unpack('<10Q', read_section(1, 0xB3C000, 0x50))
    dir_meta = read_section(1, 0xB3C000 + rh[3], rh[4])
    file_meta = read_section(1, 0xB3C000 + rh[7], rh[8])
    data_off = rh[9]

    def files():
        pos = 0
        while pos + 0x20 <= len(file_meta):
            parent, sibling, offset, size, h, nsz = struct.unpack('<IIQQII', file_meta[pos:pos + 0x20])
            name = file_meta[pos + 0x20:pos + 0x20 + nsz].decode('utf-8', 'replace')
            yield name, offset, size
            pos += (0x20 + nsz + 3) & ~3

    target = [x for x in files() if x[0] == 'scr.pack'][0]
    scr = read_section(1, 0xB3C000 + data_off + target[1], target[2])

    os.makedirs(outdir, exist_ok=True)
    dec = decrypt_scr_pack(scr)
    with open(os.path.join(outdir, 'scr_dec.bin'), 'wb') as w:
        w.write(dec)
    lines = extract_lines(dec)
    with open(os.path.join(outdir, 'Paradigm Paradox_全文本.txt'), 'w', encoding='utf-8-sig', newline='\n') as w:
        for ln in lines:
            w.write(ln + '\n')
    print('lines:', len(lines))


if __name__ == '__main__':
    main()
