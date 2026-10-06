"""PS2 .HD/.BIN extractor for the *Hakarena Heart*-type engine.

Based on the reverse-engineering write-up (srpopty, 2024) for an engine whose
.HD/.BIN layout (SCENEDAT / SCENE_ID / NORMAL / SYSTEM / *_ID) matches this game.

.HD  = index of 4-byte little-endian sizes (one per file, order == .BIN order)
.BIN = files laid out sequentially, each padded to a 0x800 sector (0xFF fill)
Compressed BINs: NORMAL, SCENE_ID, SCENEDAT  (custom queue + transpose algorithm)
"""
import os
import sys
import struct

SECTOR = 0x800


def hex2short(b):
    return struct.unpack("<i", b[:4])[0]


def decompress_chunk(data, size, step):
    result = bytearray()
    j = size // step
    i = 0
    k = j * step
    if j > 0:
        pos = 0
        while True:
            while pos < k:
                result.append(data[pos])
                pos += j
            i += 1
            if i >= j:
                break
            pos = i
    while k < size:
        result.append(data[k])
        k += 1
    return bytes(result)


def decompress_data(data, size, step):
    raw_size = size
    result = bytearray()
    queue = [[6, 0x00] for _ in range(6)]

    def upd(lv, ele):
        if lv >= 5:
            queue[5] = queue[4]
        if lv >= 4:
            queue[4] = queue[3]
        if lv >= 3:
            queue[3] = queue[2]
        if lv >= 2:
            queue[2] = queue[1]
        if lv >= 1:
            queue[1] = queue[0]
        queue[0] = ele

    pos = 8
    guard = 0
    while size > 0:
        guard += 1
        if guard > len(data) * 4 + 16:
            break
        if pos >= len(data):
            break
        instr = data[pos]
        command = instr >> 5
        length = instr & 0x1F
        pos += 1
        if command == 6:
            char = data[pos]
            upd(command, [6, char])
            result += bytes([char]) * (length + 2)
            pos += 1
            size -= length + 2
        elif command == 7:
            sub = data[pos:pos + length + 1]
            upd(command, [7, sub])
            result += sub
            pos += length + 1
            size -= length + 1
        else:
            ref = queue[command]
            upd(command, ref)
            if ref[0] == 6:
                result += bytes([ref[1]]) * (length + 2)
                size -= length + 2
            elif ref[0] == 7:
                dp = length >> 2
                dl = length & 3
                result += ref[1][dp:dp + dl + 1]
                size -= dl + 1
            else:
                return decompress_chunk(result, raw_size, step)
    return decompress_chunk(result, raw_size, step)


def classify(data):
    if data[:4] == b"TIM2":
        return ".tm2"
    if data[:2] == b"BM":
        return ".bmp"
    if data[:1] == b"[":
        return ".lst"
    if len(data) > 4 and hex2short(data[:4]) == 0x4952FAFA:
        return ".cnut"
    return ".dat"


def extract(prefix, outdir, compressed):
    hd = open(prefix + ".HD", "rb").read()
    b = open(prefix + ".BIN", "rb").read()
    os.makedirs(outdir, exist_ok=True)
    n = len(hd) // 4
    pos = 0
    table = []
    for i in range(n):
        size = hex2short(hd[i * 4:i * 4 + 4])
        if size <= 0:
            continue
        chunk = b[pos:pos + size]
        pos += size
        pos = ((pos + SECTOR - 1) // SECTOR) * SECTOR
        data = chunk
        if compressed and len(chunk) >= 8:
            try:
                data = decompress_data(chunk, hex2short(chunk[:4]), hex2short(chunk[4:8]))
            except Exception as e:
                data = chunk
        ext = classify(data)
        fn = os.path.join(outdir, "%05d%s" % (i, ext))
        with open(fn, "wb") as f:
            f.write(data)
        table.append((i, size, len(data), ext))
    return table


if __name__ == "__main__":
    prefix = sys.argv[1]
    out = sys.argv[2]
    comp = (prefix.endswith("NORMAL") or prefix.endswith("SCENE_ID")
            or prefix.endswith("SCENEDAT"))
    tbl = extract(prefix, out, comp)
    from collections import Counter
    print("files:", len(tbl), "exts:", Counter(t[3] for t in tbl))
