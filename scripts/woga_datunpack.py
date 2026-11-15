"""Tennenouji / woga AIR `.dat` 解包器。

实测结构（RAKIDOMania black dog）：
    [u8 x4 头] + raw deflate 流 + [u8 x4 头] + raw deflate 流 + …

每段用 zlib.decompressobj(-15) 解，eof 后剩余数据即下一段的起点。
第一段解出 JSON（package 清单），其余段是资源本体。

用法：
    python scripts/woga_datunpack.py <file.dat> <outdir>
"""
import json
import os
import sys
import zlib


def unpack(path, outdir=None, verbose=True):
    d = open(path, 'rb').read()
    pos = 4                     # 只有文件开头有 4 字节文件头，之后各段直接是 deflate 流
    segs = []
    n = len(d)
    while pos + 4 < n:
        hdr = b''
        o = zlib.decompressobj(-15)
        try:
            body = o.decompress(d[pos:])
        except Exception as e:
            if verbose:
                print('  seg %-4d @%#x FAIL %s' % (len(segs), pos, str(e)[:60]))
            break
        used = (n - pos) - len(o.unused_data)
        segs.append((pos, hdr, body, used))
        if not o.eof:
            if verbose:
                print('  seg %-4d @%#x truncated (no EOF), got %d' % (len(segs) - 1, pos, len(body)))
            break
        pos = pos + used
        if used <= 0:
            break
    if verbose:
        print('%s: %d segments, consumed %d/%d bytes' % (os.path.basename(path), len(segs), pos, n))
        tot = sum(len(b) for _, _, b, _ in segs)
        print('  total inflated %d bytes' % tot)
    if outdir:
        os.makedirs(outdir, exist_ok=True)
        index = []
        for i, (off, hdr, body, used) in enumerate(segs):
            kind = 'bin'
            if body[:1] in (b'{', b'['):
                try:
                    json.loads(body.decode('utf-8'))
                    kind = 'json'
                except Exception:
                    pass
            elif body[:8] == b'\x89PNG\r\n\x1a\n':
                kind = 'png'
            elif body[:4] == b'OggS':
                kind = 'ogg'
            elif body[:2] == b'\xff\xfb' or body[:2] == b'\xff\xf3':
                kind = 'mp3'
            ext = {'json': 'json', 'png': 'png', 'ogg': 'ogg', 'mp3': 'mp3'}.get(kind, 'bin')
            name = 'seg%04d.%s' % (i, ext)
            open(os.path.join(outdir, name), 'wb').write(body)
            index.append(dict(i=i, off=off, hdr=hdr.hex(), comp=used, size=len(body), kind=kind))
        open(os.path.join(outdir, '_index.json'), 'w', encoding='utf-8').write(
            json.dumps(index, ensure_ascii=False, indent=1))
    return segs


if __name__ == '__main__':
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else None
    unpack(src, dst)
