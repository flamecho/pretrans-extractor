#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用：NSP/NCA 就地读 romfs（不落副本）。

  python scripts/nca_romfs.py <容器> --list
  python scripts/nca_romfs.py <容器> --files [--nca=<名子串>]
  python scripts/nca_romfs.py <容器> --get <outdir> [--nca=<名子串>] [名子串...]

支持 PFS0(NSP)；XCI 请先切出 NCA。NCA 用 base 偏移随机访问。
密钥：Standard crypto 走 key_area + key_area_key_application[keygen-1]；
      Titlekey crypto（key area 全 0）内容密钥 = titlekey，titlekek 索引自动试（结构自证）。
"""
import os, sys, struct, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import switch_nca as SN
from Crypto.Cipher import AES
from Crypto.Util import Counter

SECTOR = 0x200


class Src:
    def __init__(self, path, base=0):
        self.f = open(path, 'rb')
        self.base = base

    def read_at(self, off, n):
        self.f.seek(self.base + off)
        return self.f.read(n)


def _nca_ok(src, off):
    try:
        h = SN.xts_decrypt(bytes.fromhex(KEYS['header_key'][:32]),
                           bytes.fromhex(KEYS['header_key'][32:64]), 0, src.read_at(off, 0x1200))
        return h[0x200:0x204] == b'NCA3'
    except Exception:
        return False


def parse_xci(src, path):
    """XCI：找含 .nca 的 HFS0（rom_area_start_page 优先，否则前 64 MB 扫），
    数据起点用三种候选逐一「解 NCA 头自证」挑选 —— 重打包档不一定 0x200 对齐、也不一定紧挨头部。"""
    fs = os.path.getsize(path)
    page = struct.unpack_from('<I', src.read_at(0x104, 4), 0)[0]
    rom = page * 0x200
    h = src.read_at(rom, 0x1000)
    cands = []
    if h[:4] == b'HFS0':
        cands.append(rom)
    buf = src.read_at(0, min(fs, 64 << 20))
    i = 0
    while True:
        j = buf.find(b'HFS0', i)
        if j < 0:
            break
        i = j + 1
        if j in cands:
            continue
        n0, s0 = struct.unpack_from('<II', buf, j + 4)
        st = j + 0x10 + n0 * 0x40
        if n0 > 4096 or s0 > 1 << 20 or st + s0 > len(buf):
            continue
        nm = buf[st:st + s0]
        if b'.nca' in nm:
            cands.append(j)
    if not cands:
        raise SystemExit('XCI: no HFS0 with .nca')
    hoff = cands[0]
    h = src.read_at(hoff, 0x1000)
    num, strsz = struct.unpack_from('<II', h, 4)
    names = []
    p = hoff + 0x10 + num * 0x40
    st = src.read_at(p, strsz)
    k = 0
    for _ in range(num):
        e = st.find(b'\x00', k)
        names.append(st[k:e].decode('utf-8', 'replace'))
        k = e + 1
    sizes = [struct.unpack_from('<Q', src.read_at(hoff + 0x10 + idx * 0x40 + 8, 8), 0)[0]
             for idx in range(num)]
    total = sum(sizes)
    bases = [hoff + 0x10 + num * 0x40 + strsz, fs - total, rom]
    base = None
    for b in bases:
        if b < 0 or b >= fs:
            continue
        if _nca_ok(src, b):
            base = b
            print('[i] XCI data base = 0x%x (HFS0@0x%x, %d files)' % (b, hoff, num))
            break
    if base is None:
        raise SystemExit('XCI: NCA 头在三个候选起点都解不出')
    ents = []
    cur = base
    for nm, sz in zip(names, sizes):
        ents.append([cur, sz, 0, nm])
        cur += sz
    return ents


def parse_pfs0(src):
    h = src.read_at(0, 0x10)
    assert h[:4] == b'PFS0', 'not PFS0'
    n, strsz = struct.unpack_from('<II', h, 4)
    ents = []
    for i in range(n):
        off, size, so, _ = struct.unpack('<QQII', src.read_at(0x10 + i * 0x18, 0x18))
        ents.append([off, size, so, ''])
    strtab = src.read_at(0x10 + n * 0x18, strsz)
    data = 0x10 + n * 0x18 + strsz
    for e in ents:
        s = e[2]
        e[3] = strtab[s:strtab.index(b'\0', s)].decode()
        e[0] += data          # 绝对偏移
    return ents


class Sec:
    """段内随机读（AES-CTR）。★CTR 低位按 **NCA 内相对偏移/16**，不含容器基址。"""
    def __init__(self, src, nca_base, sec_off, key, ctr_hi):
        self.src, self.nb, self.off, self.key, self.hi = src, nca_base, sec_off, key, ctr_hi

    def read(self, rel, n):
        nca_rel = self.off + rel
        a = self.nb + nca_rel
        al = nca_rel & ~0xF
        ctr = self.hi + (al // 16).to_bytes(8, 'big')
        e = self.src.read_at(self.nb + al, ((n + 15) // 16) * 16 + 16)
        p = AES.new(self.key, AES.MODE_CTR,
                    counter=Counter.new(128, initial_value=int.from_bytes(ctr, 'big'))).decrypt(e)
        return p[nca_rel - al:nca_rel - al + n]


def nca_hdr(src, base):
    hdr = SN.xts_decrypt(bytes.fromhex(KEYS['header_key'][:32]),
                         bytes.fromhex(KEYS['header_key'][32:64]), 0, src.read_at(base, 0x1200))
    return hdr


KEYS = SN.load_keys('_sw/prod_fixed.keys')


def titlekey_cands(tik_block, hdr, tik_from_keys=None):
    """返回 (rev, key) 候选：titlekek 解出的 titlekey，以及 tik_block 本身（有些包是明文）。"""
    revs = []
    for r in (hdr[0x220] - 1, hdr[0x21C], hdr[0x206] - 1, hdr[0x207], 0x0f, 0x0e, 0x0d):
        if 0 <= r < 0x20 and r not in revs:
            revs.append(r)
    out = []
    if tik_from_keys:
        out.append(('title.keys', tik_from_keys))
    for r in revs:
        k = KEYS.get('titlekek_%02x' % r)
        if not k:
            continue
        try:
            out.append(('titlekek_%02x' % r, AES.new(bytes.fromhex(k), AES.MODE_ECB).decrypt(tik_block).hex()))
        except Exception:
            pass
    out.append(('tik-block-as-is', tik_block.hex()))
    return out


def open_nca(src, base):
    hdr = nca_hdr(src, base)
    if hdr[0x200:0x204] != b'NCA3':
        return None
    keygen = hdr[0x220]
    secs = []
    for i in range(4):
        e = hdr[0x240 + i * 0x10:0x240 + i * 0x10 + 0x10]
        secs.append((int.from_bytes(e[0:4], 'little') * 0x200,
                     int.from_bytes(e[4:8], 'little') * 0x200))
    sect = None
    for s in range(4):
        b = 0x400 + s * 0x200
        if hdr[b + 0x08:b + 0x0C] in (b'IVFC', b'ROMF', b'PFS0'):
            sect = s
            break
    return dict(hdr=hdr, keygen=keygen, secs=secs, sect=sect,
                rights=hdr[0x230:0x240], progid=struct.unpack_from('<Q', hdr, 0x210)[0])


def try_keys(src, base, info, cands):
    """依次用候选内容密钥试解，用「romfs 头自洽」作结构自证。返回 (key, ctr_hi, name, romfs_off, v)。"""
    s = info['sect']
    if s is None:
        return None
    sec_off, sec_end = info['secs'][s]
    hi = struct.unpack_from('<Q', info['hdr'], 0x400 + s * 0x200 + 0x140)[0].to_bytes(8, 'big')
    for name, khex in cands:
        try:
            key = bytes.fromhex(khex)
        except ValueError:
            continue
        if len(key) != 16:
            continue
        sc = Sec(src, base, sec_off, key, hi)
        off, v = romfs_scan(sc, sec_end - sec_off)
        if off is not None:
            return key, hi, name, off, v
    return None


def std_cands(hdr, keygen):
    ka = hdr[0x300:0x340]
    out = []
    kak = KEYS.get('key_area_key_application_%02x' % max(keygen - 1, 0))
    if kak:
        for i in range(4):
            blk = ka[i * 16:i * 16 + 16]
            if blk == b'\0' * 16:
                continue
            out.append(('ka[%d]' % i, AES.new(bytes.fromhex(kak), AES.MODE_ECB).decrypt(blk).hex()))
    return out


def romfs_scan(sc, size):
    chunk = sc.read(0, min(0x4000000, size))
    for i in range(0, len(chunk) - 0x50 + 1, 0x10):
        v = struct.unpack_from('<10Q', chunk, i)
        if v[0] != 0x50:
            continue
        if v[1] >= 0x50 and v[3] > v[1] and v[5] > v[3] and v[7] > v[5] \
                and v[7] + v[8] <= size and 0x50 <= v[9] < size:
            return i, v
    return None, None


def list_romfs(sc, roff, v):
    """RomFS：dir/file 表的 parent 字段是**表内字节偏移**（不是下标），必须按偏移建表。"""
    dm = sc.read(roff + v[3], v[4])
    fm = sc.read(roff + v[7], v[8])
    dirs = {}
    p = 0
    while p + 0x18 <= len(dm):
        par, sib, ch, fi, hsh, nl = struct.unpack_from('<IIIIII', dm, p)
        dirs[p] = {'parent': par, 'name': dm[p + 0x18:p + 0x18 + nl].decode('utf-8', 'replace')}
        p += (0x18 + nl + 3) & ~3
    files = []
    p = 0
    while p + 0x20 <= len(fm):
        par, sib, fo, sz, hsh, nl = struct.unpack_from('<IIQQII', fm, p)
        files.append({'parent': par, 'off': fo, 'size': sz,
                      'name': fm[p + 0x20:p + 0x20 + nl].decode('utf-8', 'replace')})
        p += (0x20 + nl + 3) & ~3

    cache = {}

    def dpath(off):
        if off in cache:
            return cache[off]
        d = dirs.get(off)
        if d is None or off == 0:
            cache[off] = ''
            return ''
        up = dpath(d['parent'])
        cache[off] = (up + '/' + d['name']) if up else d['name']
        return cache[off]

    data_off = v[9] if 0x50 <= v[9] < 0x7fffffff else 0x200
    ents = []
    for fl in files:
        ents.append((dpath(fl['parent']), fl['name'], roff + data_off + fl['off'], fl['size']))
    return ents


def main():
    path = sys.argv[1]
    args = sys.argv[2:]
    want_nca = None
    outdir = None
    wants = []
    mode = None
    i = 0
    while i < len(args):
        a = args[i]
        if a == '--list':
            mode = 'list'
        elif a == '--files':
            mode = 'files'
        elif a == '--get':
            mode = 'get'
        elif a.startswith('--nca='):
            want_nca = a.split('=', 1)[1]
        elif mode == 'get' and outdir is None:
            outdir = a
        else:
            wants.append(a)
        i += 1
    src = Src(path)
    if src.read_at(0x100, 4) == b'HEAD':
        ents = parse_xci(src, path)
    else:
        ents = parse_pfs0(src)
    tiks = {}
    for off, size, so, name in ents:
        if name.endswith('.tik'):
            tiks[name] = src.read_at(off, size)
    for off, size, so, name in ents:
        print('%14d  @0x%X  %s' % (size, off, name))
    if mode == 'list' and not want_nca:
        return
    for off, size, so, name in ents:
        if not name.endswith('.nca'):
            continue
        if want_nca and want_nca.lower() not in name.lower():
            continue
        info = open_nca(src, off)
        if not info:
            print('  [!] %s 头解不出' % name)
            continue
        print('=== %s progid=%016X keygen=%d sect=%s' % (name, info['progid'], info['keygen'], info['sect']))
        if info['sect'] is None:
            continue
        cands = []
        if info['rights'] != b'\0' * 16:
            blk = None
            for tname, tb in tiks.items():
                if tb[0x2A0:0x2B0] == info['rights']:
                    blk = tb[0x180:0x190]
                    break
            if blk:
                cands += titlekey_cands(blk, info['hdr'])
        cands += std_cands(info['hdr'], info['keygen'])
        hit = try_keys(src, off, info, cands)
        if not hit:
            print('  [!] 段密钥未确定')
            continue
        key, hi, src_name, roff, v = hit
        print('  key=%s (%s) ctr_hi=%s romfs@+0x%x' % (key.hex(), src_name, hi.hex(), roff))
        s = info['sect']
        sec_off = info['secs'][s][0]
        sc = Sec(src, off, sec_off, key, hi)
        ents2 = list_romfs(sc, roff, v)
        print('  文件 %d' % len(ents2))
        if mode in ('files', 'list'):
            for d, n, o, sz in sorted(ents2):
                print('%12d  %s%s%s' % (sz, d, '/' if d else '', n))
        elif mode == 'get':
            os.makedirs(outdir, exist_ok=True)
            for d, n, o, sz in ents2:
                full = (d + '/' + n).lstrip('/')
                if wants and not any(w.lower() in full.lower() for w in wants):
                    continue
                dst = os.path.join(outdir, n)
                with open(dst, 'wb') as g:
                    pos = 0
                    while pos < sz:
                        k = min(1 << 24, sz - pos)
                        g.write(sc.read(o + pos, k))
                        pos += k
                print('[+] %s -> %s (%d)' % (full, dst, sz))


if __name__ == '__main__':
    main()
