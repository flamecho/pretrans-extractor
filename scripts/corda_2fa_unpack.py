#!/usr/bin/env python3
"""金色のコルダ2f アンコール (PSP) CDAR v4 解包器.

CDAR v4 布局（小端序）:
  0x00 "CDAR"
  0x04 u32 version (=4)
  0x08 u32 entryCount
  0x0C u32 hash
  0x10 entryCount * u32  hashes (sorted)
  0x10+4n entryCount * 12  entries: [offset:u32][decompSize:u32][size:u32]
  data 区从 (0x10+16n) 起，每个 entry 的 offset 相对本容器起始，0x800 对齐。

用法:
  python corda2f_unpack.py <DATA.BIN> <outdir>
  仅解包 - 会递归展开嵌套 CDAR；zlib 条目 inflate。
"""
import sys, os, zlib, struct

def parse_cdar(buf, depth=0, chain="", out=None, log=None):
    """解析一个 CDAR v4 blob（整个文件已在内存 buf），返回叶子列表。"""
    if len(buf) < 16 or buf[:4] != b'CDAR':
        return []
    ver, cnt, h = struct.unpack_from('<III', buf, 4)
    assert ver == 4, f"unexpected CDAR version {ver}"
    base = 0x10 + 4 * cnt          # entry table offset
    leaves = []
    for i in range(cnt):
        off, dec, sz = struct.unpack_from('<III', buf, base + 12 * i)
        if sz == 0:
            continue
        seg = buf[off:off + sz]
        path = f"{chain}{i}"
        if seg[:4] == b'CDAR' and struct.unpack_from('<I', seg, 4)[0] == 4:
            sub = parse_cdar(seg, depth + 1, path + "/", out, log)
            leaves.extend(sub)
        else:
            data = seg
            if dec != sz and seg[:1] == b'\x78':
                try:
                    data = zlib.decompress(seg)
                except Exception as e:
                    if log: log.append(("inflate-fail", path, str(e)))
            leaves.append((path, off, dec, sz, data))
    return leaves


def main():
    src = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else None
    raw = open(src, 'rb').read()
    print(f"read {len(raw):,} bytes")
    log = []
    leaves = parse_cdar(raw, 0, "", None, log)
    print(f"leaf files: {len(leaves)}")
    print(f"log: {log[:10]}")
    if outdir:
        os.makedirs(outdir, exist_ok=True)
        for path, off, dec, sz, data in leaves:
            fn = os.path.join(outdir, path.replace('/', '_') + '.bin')
            with open(fn, 'wb') as g:
                g.write(data)


if __name__ == '__main__':
    main()
