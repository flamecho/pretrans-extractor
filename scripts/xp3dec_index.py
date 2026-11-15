# -*- coding: utf-8 -*-
"""XP3 索引解析（通用）：Kirikiri XP3 的 File/info/segm/adlr 块逐个消费，导出 JSON + 成员名清单。

用法：
  python xp3dec_index.py <data.xp3> [out.json] [out.list.txt]

要点（TARHS『図書室のネヴァジスタ THE FOOL』实证）：
- 头 `XP3\\r\\n \\n\\x1a\\x8b` + `u64 index_offset @0x20`；zlib 流实际起于 `index_offset + 17`（`78 da`）。
- 块必须按 `头4字节 + u64 size` 逐个消费；按固定 28 B 步进会 struct.error。
- info = `[u32 flags][u64 psize][u64 usize][u16 nlen][UTF-16LE name]`；
  **psize = 解压后长度，usize = 磁盘长度**（与直觉相反）。
- segm = 28 B `<IQQQ`：`(flags, off, a, b)`，`a = psize`、`b = 磁盘存储长`。
- adlr = u32 校验值（本作等于明文的 zlib.adler32，可用于验证解密结果）。
- flags & 1 == 0 的文件内容**仍可能是密文**：不要拿文件头 magic 当已知明文反解密钥。
"""
import io
import os
import struct
import sys
import zlib
import json


def parse(path):
    sz = os.path.getsize(path)
    with io.open(path, 'rb') as f:
        head = f.read(32)
        if not head.startswith(b'XP3'):
            raise SystemExit('not an XP3: %r' % head[:8])
        idx = struct.unpack_from('<Q', head, 0x20)[0] if len(head) >= 0x28 else None
        # 有些打包器把 index_offset 写在 0x0b 之后
        if idx is None or idx >= sz:
            f.seek(0)
            b = f.read(64)
            idx = struct.unpack_from('<Q', b, 0x1c)[0]
        # zlib 流起点：从 idx 起向后找第一处 78 9c / 78 da
        start = None
        for pad in range(0, 64):
            f.seek(idx + pad)
            if f.read(2) in (b'\x78\x9c', b'\x78\xda', b'\x78\x01'):
                start = idx + pad
                break
        if start is None:
            raise SystemExit('zlib stream not found near %#x' % idx)
        f.seek(start)
        raw = f.read(sz - start)
    out = zlib.decompressobj().decompress(raw)
    entries = []
    p = 0
    while p + 12 <= len(out):
        tag = out[p:p + 4]
        size = struct.unpack_from('<Q', out, p + 4)[0]
        if tag != b'File':
            break
        payload = out[p + 12:p + 12 + size]
        q = 0
        name, segs, info, adlr = None, [], {}, None
        while q + 12 <= len(payload):
            t = payload[q:q + 4]
            s = struct.unpack_from('<Q', payload, q + 4)[0]
            sp = payload[q + 12:q + 12 + s]
            if t == b'info':
                flags = struct.unpack_from('<I', sp, 0)[0]
                psize = struct.unpack_from('<Q', sp, 4)[0]
                usize = struct.unpack_from('<Q', sp, 12)[0]
                nlen = struct.unpack_from('<H', sp, 20)[0]
                name = sp[22:22 + nlen * 2].decode('utf-16-le', 'replace')
                info = dict(flags=flags, psize=psize, usize=usize)
            elif t == b'segm':
                for i in range(0, len(sp) - 27, 28):
                    segs.append(struct.unpack_from('<IQQQ', sp, i))
            elif t == b'adlr':
                adlr = struct.unpack_from('<I', sp, 0)[0]
            q += 12 + s
        entries.append(dict(name=name, adlr=adlr, segs=segs, **info))
        p += 12 + size
    return entries, idx, start, len(out)


def main():
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + '_index.json'
    lst = sys.argv[3] if len(sys.argv) > 3 else None
    entries, idx, start, dlen = parse(src)
    print('index_offset %#x / zlib at %#x / inflated %d B / entries %d' % (idx, start, dlen, len(entries)))
    with io.open(dst, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=0)
    print('wrote', dst)
    if lst:
        with io.open(lst, 'w', encoding='utf-8', newline='\n') as g:
            for e in sorted(entries, key=lambda x: x['name'] or ''):
                g.write((e['name'] or '?') + '\n')
        print('wrote', lst)
    exts = {}
    for e in entries:
        k = os.path.splitext(e['name'] or '')[1].lower()
        exts[k] = exts.get(k, 0) + 1
    print('exts', sorted(exts.items(), key=lambda kv: -kv[1]))


if __name__ == '__main__':
    main()
