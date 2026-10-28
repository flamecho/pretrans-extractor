#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""絶対階級学園 —— 从 prog.nca 流式取 romfs 指定文件（不落 6GB 副本）。

用法:
  python scripts/zettaikyuu_romfs.py list <nca> <tik_enc_hex>
  python scripts/zettaikyuu_romfs.py get  <nca> <tik_enc_hex> <outdir> [name子串...]
"""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import switch_nca as SN
from Crypto.Cipher import AES
from Crypto.Util import Counter


class Rom:
    def __init__(self, f, sec_off, sec_size, key, ctr_hi):
        self.f, self.off, self.size, self.key, self.hi = f, sec_off, sec_size, key, ctr_hi
        self.base = 0

    def rd(self, rel, n):
        a = self.off + self.base + rel
        al = a & ~0xF
        ctr = self.hi + (al // 16).to_bytes(8, 'big')
        self.f.seek(al)
        e = self.f.read(((n + 15) // 16) * 16 + 16)
        p = AES.new(self.key, AES.MODE_CTR,
                    counter=Counter.new(128, initial_value=int.from_bytes(ctr, 'big'))).decrypt(e)
        return p[a - al:a - al + n]


def parse(nca, tik_enc):
    keys = SN.load_keys('_sw/prod_fixed.keys')
    f, hdr, keygen, secs, ka, fsinfo = SN.parse(nca, keys, None)
    # keygen 实际在 0x220（0x206 是 crypto type）；titlekek 索引 = keygen-1，带结构自证回退
    rev_cands = [hdr[0x220] - 1, hdr[0x21C], keygen - 1]
    # 找 romfs 段: FS 头 magic IVFC @0x400+s*0x200+0x08
    for s in range(4):
        b = 0x400 + s * 0x200
        if hdr[b + 0x08:b + 0x0C] == b'IVFC':
            secno = s
            break
    else:
        raise SystemExit('no IVFC section')
    sec_off, sec_end = secs[secno]
    ctr_hi = struct.unpack_from('<Q', hdr, 0x400 + secno * 0x200 + 0x140)[0].to_bytes(8, 'big')
    for rev in rev_cands:
        try:
            titlekey = AES.new(bytes.fromhex(keys['titlekek_%02x' % rev]),
                               AES.MODE_ECB).decrypt(bytes.fromhex(tik_enc))
        except KeyError:
            continue
        r = Rom(f, sec_off, sec_end - sec_off, titlekey, ctr_hi)
        chunk = r.rd(0, min(0x4000000, r.size))
        cand = None
        for i in range(0, len(chunk) - 0x50, 0x10):
            v = struct.unpack_from('<10Q', chunk, i)
            if v[0] != 0x50:
                continue
            if not (v[1] > 0x50 and v[3] > v[1] and v[5] > v[3] and v[7] > v[5]):
                continue
            cand = i
            break
        if cand is not None:
            print('[i] titlekek rev=%d titlekey=%s' % (rev, titlekey.hex()))
            break
    else:
        raise SystemExit('romfs header not found')
    r.base = cand
    h = r.rd(0, 0x50)
    v = struct.unpack('<10Q', h)
    print('[i] romfs@+0x%x hdr=%s' % (cand, [hex(x) for x in v]))
    dirmeta_off, dirmeta_sz = v[3], v[4]
    filemeta_off, filemeta_sz = v[7], v[8]
    dm = r.rd(dirmeta_off, dirmeta_sz)
    fm = r.rd(filemeta_off, filemeta_sz)
    dirs, files = [], []
    p = 0
    while p + 0x18 <= len(dm):
        par, sib, ch, fi, hsh, nl = struct.unpack_from('<IIIIII', dm, p)
        dirs.append({'parent': par, 'name': dm[p + 0x18:p + 0x18 + nl].decode('utf-8', 'replace')})
        p += (0x18 + nl + 3) & ~3
    p = 0
    while p + 0x20 <= len(fm):
        par, sib, off, sz, hsh, nl = struct.unpack_from('<IIQQII', fm, p)
        files.append({'parent': par, 'off': off, 'size': sz,
                      'name': fm[p + 0x20:p + 0x20 + nl].decode('utf-8', 'replace')})
        p += (0x20 + nl + 3) & ~3
    for i, d in enumerate(dirs):
        path, cur, g = '', i, 0
        while cur > 0 and g < 32:
            path = dirs[cur]['name'] + ('/' + path if path else '')
            cur = dirs[cur]['parent']
            g += 1
        d['path'] = path
    # data 起点：头里的 data_off 若不可信则用「表前空隙」推定，实测 0x200
    data_off = v[9] if 0x50 <= v[9] < dirmeta_off else 0x200
    ents = []
    for fl in files:
        d = dirs[fl['parent']]['path'] if fl['parent'] < len(dirs) else ''
        ents.append((d, fl['name'], data_off + fl['off'], fl['size']))
    return r, ents


def main():
    cmd, nca, tik = sys.argv[1], sys.argv[2], sys.argv[3]
    r, ents = parse(nca, tik)
    if cmd == 'list':
        for d, n, o, s in sorted(ents):
            print('%12d  %s%s%s' % (s, d, '/' if d else '', n))
        return
    outdir = sys.argv[4]
    wants = sys.argv[5:]
    os.makedirs(outdir, exist_ok=True)
    for d, n, o, s in ents:
        full = (d + '/' + n).lstrip('/')
        if wants and not any(w.lower() in full.lower() for w in wants):
            continue
        dst = os.path.join(outdir, n)
        with open(dst, 'wb') as g:
            pos = 0
            while pos < s:
                k = min(1 << 24, s - pos)
                g.write(r.rd(o + pos, k))
                pos += k
        print('[+] %s -> %s (%d)' % (full, dst, s))


if __name__ == '__main__':
    main()
