# -*- coding: utf-8 -*-
"""アンジェリーク エトワール (PS2) DATA02 脚本解包

DATA02 的 PACK(H2) 结构：
  +0x00 'PACK'
  +0x04 u32 nameLen
  +0x08 byte[nameLen]  KEY（密钥，每文件不同）
  +0x08+nameLen  u32 A, B, doff, dsize, 1, count, recSize(64), 0
  A     记录表（count * 64，纯名字）
  doff  数据区

数据区 = 若干段，每段 [u32 v][stream]，整段与 key 循环 XOR（每段 key 从 0 起）
  v == 段长-4  -> type2 (MTF+RLE)
  否则 v 是 maskBits -> type1 (LZSS)

解压产物 = SCPT 脚本容器。
"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from etoile_unpack import load_pair  # noqa: E402
from emu_dec import dec1, dec2  # noqa: E402

CAP = 1 << 21  # 2 MiB，脚本不会更大


def _xor(seg, key):
    n = len(key)
    return bytes(c ^ key[i % n] for i, c in enumerate(seg))


def _tail(blob):
    """按 SCPT 头里的段大小裁掉尾部填充"""
    if len(blob) < 0x20:
        return None
    hdr = struct.unpack('<I', blob[12:16])[0]
    if hdr + 0x20 > len(blob):
        return None
    end = max((i for i, x in enumerate(blob) if x != 0), default=0) + 1
    return blob[:end]


def _try1(pl):
    if not (4 <= len(pl)):
        return None
    v = struct.unpack('<I', pl[:4])[0]
    if v == 0 or v > 4 * len(pl):
        return None
    try:
        out, _ = dec1(pl, CAP)
    except Exception:
        return None
    if out[:4] != b'SCPT':
        return None
    return _tail(out)


def _try2(pl):
    v = struct.unpack('<I', pl[:4])[0]
    if v + 4 > len(pl):
        return None
    try:
        out, _ = dec2(pl[:4 + v], CAP)
    except Exception:
        return None
    if not out or out[:4] != b'SCPT':
        return None
    return _tail(out)


def unpack_entry(buf):
    if buf[:4] != b'PACK':
        return None, []
    nl = struct.unpack('<I', buf[4:8])[0]
    if nl <= 0 or nl > 0x400 or 8 + nl + 32 > len(buf):
        return None, []
    key = buf[8:8 + nl]
    E = 8 + nl
    A, B, doff, ds, _one, cnt, rec, _z = struct.unpack('<8I', buf[E:E + 32])
    if doff + ds > len(buf) or A + B != doff:
        return None, []
    seg = buf[doff:doff + ds]
    outs = []
    pos = 0
    while pos + 8 < len(seg):
        pl = _xor(seg[pos:], key)
        v = struct.unpack('<I', pl[:4])[0]
        blob = None
        if v == len(pl) - 4:
            blob = _try2(pl)
        else:
            blob = _try1(pl)
            if blob is None:
                blob = _try2(pl)
        if blob is None:
            break
        outs.append(blob)
        pos += 4 + (v if v == len(pl) - 4 else len(pl) - 4)
        if v != len(pl) - 4:
            break
    return key, outs


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(VNTRANS_HOME, '_src_etoile')
    outdir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(VNTRANS_HOME, '_work_etoile/scpt')
    os.makedirs(outdir, exist_ok=True)
    sizes, ents, data = load_pair(root + '/DATA02')
    names = [x for x in data[:sizes[0]].decode('cp932', 'replace').split('\r\n') if x]
    ok = 0
    fail = []
    for i in range(1, len(ents)):
        o, s = ents[i]
        key, outs = unpack_entry(data[o:o + s])
        if outs:
            ok += 1
            nm = (names[i] if i < len(names) else 'x%d' % i).replace('/', '_')
            for k, b in enumerate(outs):
                open(os.path.join(outdir, '%05d_%s_%d.scpt' % (i, nm, k)), 'wb').write(b)
        else:
            fail.append((i, names[i] if i < len(names) else '?'))
    print('ok=%d fail=%d' % (ok, len(fail)))
    for f in fail[:20]:
        print('  fail', f)


if __name__ == '__main__':
    main()
