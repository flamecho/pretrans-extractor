#!/usr/bin/env python3
"""Himauri (SH System) HXP 容器解包 —— Him4 / Him5

格式与解压算法依据：
  CoffeeFlux/Fushigi-Tools  fushigi/parser.py + fushigi/unpacker.py
  （Himauri Script Engine，亦称 SH System）

容器
  Him4: [4B 'Him4'][u32 count][u32 offset × count]
        每个条目 @offset: [u32 comp_size][u32 orig_size][data]
  Him5: [4B 'Him5'][u32 folder_count][{u32 size, u32 offset} × folder_count]
        每个 folder @offset 长度 size，内含记录序列：
          [u8 namelen(+6)][u32 BE file_offset][name][0x00]
        每个 file @file_offset: [u32 comp_size][u32 orig_size][data]
  comp_size == 0 ⇒ data 为原始未压缩字节；否则用下方 LZ 解压到 orig_size。

用法
  python scripts/himpac.py list  <a.hxp>
  python scripts/himpac.py extract <a.hxp> <outdir>
"""
import os
import struct
import sys


def decompress(raw, target_len):
    """Himauri LZ —— 逐字节移植自 Fushigi-Tools unpacker.decompress()。"""
    out = bytearray(target_len)
    si = 0
    di = 0
    code = 0
    back = 0
    n = len(raw)
    while si < n and di < target_len:
        if code == 0:
            code = raw[si]
            si += 1
            if code < 0x20:
                back = 0
                if code < 0x1D:
                    code += 1
                elif code == 0x1D:
                    code = raw[si] + 0x1E
                    si += 1
                elif code == 0x1E:
                    code = raw[si]
                    si += 1
                    code = (code << 8) | raw[si]
                    si += 1
                    code += 0x11E
                else:  # 0x1F
                    code = raw[si]; si += 1
                    code = (code << 8) | raw[si]; si += 1
                    code = (code << 8) | raw[si]; si += 1
                    code = (code << 8) | raw[si]; si += 1
            else:
                if code >= 0x80:
                    back = ((code & 0x1F) << 8) | raw[si]
                    si += 1
                    code = (code >> 5) & 3
                else:
                    code2 = code & 0x60
                    if code2 == 0x20:
                        back = (code >> 2) & 7
                        code &= 3
                    else:
                        code &= 0x1F
                        if code2 == 0x40:
                            back = raw[si]
                            si += 1
                            code += 4
                        else:
                            back = (code << 8) | raw[si]
                            si += 1
                            code = raw[si]
                            si += 1
                            if code == 0xFE:
                                code = raw[si]; si += 1
                                code = (code << 8) | raw[si]; si += 1
                                code += 0x102
                            elif code == 0xFF:
                                code = raw[si]; si += 1
                                code = (code << 8) | raw[si]; si += 1
                                code = (code << 8) | raw[si]; si += 1
                                code = (code << 8) | raw[si]; si += 1
                            else:
                                code += 4
                back += 1
                code += 3

        length = code
        if di + length > target_len:
            length = target_len - di
        code -= length

        if back > 0:
            for i in range(length):
                out[di + i] = out[di + i - back]
            di += length
        else:
            out[di:di + length] = raw[si:si + length]
            si += length
            di += length

    return bytes(out)


def read_pac(path):
    d = open(path, "rb").read()
    magic = d[:4].decode("latin1")
    count, = struct.unpack_from("<I", d, 4)
    u = lambda o: struct.unpack_from("<I", d, o)[0]

    if magic == "Him4":
        offs = [u(8 + 4 * i) for i in range(count)]
        items = []
        for i, off in enumerate(offs):
            cs, osz = struct.unpack_from("<II", d, off)
            payload = d[off + 8:off + 8 + cs] if cs else d[off + 8:off + 8 + osz]
            data = decompress(payload, osz) if cs else payload
            items.append((str(i), off, cs, osz, data))
        return magic, count, items

    if magic == "Him5":
        folders = []
        for i in range(count):
            sz, off = struct.unpack_from("<II", d, 8 + 8 * i)
            folders.append((sz, off))
        items = []
        for fi, (fsz, foff) in enumerate(folders):
            if fsz == 0:
                continue
            p = foff
            end = foff + fsz
            while p < end - 1:
                nl = d[p]
                foff2 = struct.unpack_from(">I", d, p + 1)[0]
                name = d[p + 5:p + 5 + (nl - 6)].decode("latin1")
                p += 5 + (nl - 6) + 1
                cs, osz = struct.unpack_from("<II", d, foff2)
                payload = d[foff2 + 8:foff2 + 8 + cs] if cs else d[foff2 + 8:foff2 + 8 + osz]
                data = decompress(payload, osz) if cs else payload
                items.append((name, foff2, cs, osz, data))
        return magic, count, items

    raise SystemExit("未知魔数: %r" % magic)


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    cmd, src = sys.argv[1], sys.argv[2]
    magic, count, items = read_pac(src)
    if cmd == "list":
        print(f"[i] {os.path.basename(src)}  {magic}  count={count}  entries={len(items)}")
        for name, off, cs, osz, data in items:
            tag = "LZ" if cs else "raw"
            print(f"  {name:28s} @{off:#09x} {tag} {cs:8d}->{osz:8d}  {data[:4]!r}")
    elif cmd == "extract":
        outdir = sys.argv[3]
        os.makedirs(outdir, exist_ok=True)
        for name, off, cs, osz, data in items:
            fn = os.path.join(outdir, name.replace("/", "_"))
            if not fn.endswith(".him") and data[:7] == b"Himauri":
                fn += ".him"
            open(fn, "wb").write(data)
        print(f"[i] 导出 {len(items)} 个条目 -> {outdir}")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
