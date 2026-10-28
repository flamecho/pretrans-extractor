#!/usr/bin/env python3
"""btf_unpack.py —— M2「ADVENGINE」PSB 盘 一键解包（PGD → 成员 → MDF → PSB）。

把先前 4 个一次性探针（p_carve2 / p_scn / p_scr / p_cfg）合并为可复用工具：
  carve   : INSTALL.BIN(PGD) --umd_root--> 成员文件（含 *_info.psb.m / *_body.bin）
  infos   : 各 *_info.psb.m --MDF--> *_info.psb（再喂 PsbDecompile 得 JSON）
  members : <分类>_info.json --MDF--> 该 body 内全部成员 PSB（如 scenario 的 327 个 .scn）

用法:
  python scripts/btf_unpack.py carve   <INSTALL.BIN> <fileinfo.psb.m.json> <outdir>
  python scripts/btf_unpack.py infos   <dir> <key> [keylen]
  python scripts/btf_unpack.py members <dir> <key> <name> [keylen]    # name 如 scenario/script/config
说明: <dir> 里需有 <name>_info.psb.m 与 <name>_body.bin；成员后缀取自 info 的 expire_suffix_list。
"""
import sys, os, json, zlib, mmap
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import btf_pgd as P
from btf_mdf import keystream, mdf_decrypt


def carve(install, fileinfo_json, outdir):
    f = open(install, 'rb')
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    h = P.header_desc(mm)
    print('PGD file_size', h['file_size'], 'mac80', h['mac80'])
    root = json.load(open(fileinfo_json, encoding='utf-8'))['umd_root']
    os.makedirs(outdir, exist_ok=True)
    for name, v in root.items():
        if len(v) != 3:
            print('skip (UMD direct)', name, v); continue
        _, size, off = v
        size, off = int(size), int(off)
        d, _ = P.decrypt_range(mm, off, size, h)
        p = os.path.join(outdir, name.replace('/', os.sep))
        if os.path.dirname(p):
            os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(d)
        print('%-24s %10d @%12d  %s' % (name, size, off, d[:4]))


def infos(d, key, keylen=131):
    for f in sorted(os.listdir(d)):
        if not f.endswith('_info.psb.m'):
            continue
        src = os.path.join(d, f)
        dst = src[:-2]
        plain = mdf_decrypt(open(src, 'rb').read(), key, f, keylen)
        open(dst, 'wb').write(plain)
        print('%-26s -> %s  %d B' % (f, os.path.basename(dst), len(plain)))


def members(d, key, name, keylen=131):
    info = json.load(open(os.path.join(d, name + '_info.json'), encoding='utf-8'))
    body = open(os.path.join(d, name + '_body.bin'), 'rb').read()
    suf = (info.get('expire_suffix_list') or [''])[0]
    os.makedirs(os.path.join(d, name + '_psb'), exist_ok=True)
    ok = 0
    for fn, (off, size) in info['file_info'].items():
        chunk = body[off:off + size]
        ks = keystream(key, fn + suf, keylen)
        L = len(ks)
        dec = bytes(c ^ ks[i % L] for i, c in enumerate(chunk[8:]))
        try:
            data = zlib.decompress(dec)
        except Exception as e:
            print('FAIL', fn, e); continue
        open(os.path.join(d, name + '_psb', fn + '.psb'), 'wb').write(data)
        ok += 1
    print('members ok', ok, 'suffix', suf)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'carve':
        carve(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == 'infos':
        infos(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 131)
    elif cmd == 'members':
        members(sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]) if len(sys.argv) > 5 else 131)
