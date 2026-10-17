#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GSS / LSDARC 'LSD\\x1a' codec (Takuyo gss engine).

Ported from CialloAlone / Airahc GalgameReverse  src/gss/gss_arc.cs
(original GARbro skeleton by morkt, UnpackH/D finished by devseed).

pack_method: D / R / H / W   enc_method: N / B / W / S
Packed block = "LSD\\x1a" + enc(1) + pack(1) + u32 unpacked_size + payload.
`buf_packed` (payload) starts at entry.Offset + 12 (i.e. after the 12-byte header region).
"""
import struct

# --- tables from the engine (addresses in comments) -------------------------
MASK = [  # dword_8107F828
    0x00000000,0x00000000,0x00000001,0x00000000,0x00000003,0x00000000,0x00000007,0x00000000,
    0x0000000F,0x00000000,0x0000001F,0x00000000,0x0000003F,0x00000000,0x0000007F,0x00000000,
    0x000000FF,0x00000000,0x000001FF,0x00000000,0x000003FF,0x00000000,0x000007FF,0x00000000,
    0x00000FFF,0x00000000,0x00001FFF,0x00000000,0x00003FFF,0x00000000,0x00007FFF,0x00000000,
    0x0000FFFF,0x00000000,0x0001FFFF,0x00000000,0x0003FFFF,0x00000000,0x0007FFFF,0x00000000,
    0x000FFFFF,0x00000000,0x001FFFFF,0x00000000,0x003FFFFF,0x00000000,0x007FFFFF,0x00000000,
    0x00FFFFFF,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000007,0x0000000F,
    0x0000001F,0x0000003F,0x0000007F,0x000000FF,0x000001FF,0x000003FF,0x000007FF,0x00000FFF,
    0x00001FFF,0x00003FFF,0x00007FFF,0x0000FFFF,0x0001FFFF,0x0003FFFF,0x000FFFFF,0x00000000,
    0x06050403,0x0A090807,0x0E0D0C0B,0x00000000,0x00000001,0x00000002,0x00000004,0x00000008,
    0x00000010,0x00000020,0x00000040,0x00000080,0x00000100,0x00000200,0x00000400,0x00000800,
    0x00001000,0x00002000,0x00004000,0x00000000,0xFFFF0001,0x00000000,0x00000000,0x00000001,
    0xFFFFFFFF,0xFFFFFFFF,0xFFFFFFFF,0x00000001,0x00000001,
]
D750 = [  # dword_8107F750
    0x00000000,0x00000000,0x00000001,0x00000003,0x00000007,0x0000000F,0x0000001F,0x0000003F,
    0x0000007F,0x000000FF,0x000001FF,0x000003FF,0x000007FF,0x00000FFF,0x00001FFF,0x00003FFF,
    0x00007FFF,0x0000FFFF,0x0001FFFF,0x0003FFFF,0x000FFFFF,0x00000000,0x00000000,0x00000001,
]
D7A4 = [  # dword_8107F7A4
    0x00000000,0x00000000,0x00000001,0x00000002,0x00000003,0x00000004,0x00000005,0x00000006,
    0x00000007,0x00000008,0x00000009,0x0000000A,0x0000000B,0x0000000C,0x0000000D,0x0000000E,
    0x00000000,0x00000001,0x00000002,0x00000004,0x00000008,0x00000010,0x00000020,0x00000040,
    0x00000080,0x00000100,0x00000200,0x00000400,0x00000800,0x00001000,0x00002000,0x00004000,
    0x00000000,0x00000000,0x00000000,0x00000001,0x00000000,0x00000003,0x00000000,0x00000007,
    0x00000000,0x0000000F,0x00000000,0x0000001F,0x00000000,0x0000003F,0x00000000,0x0000007F,
    0x00000000,0x000000FF,0x00000000,0x000001FF,0x00000000,0x000003FF,0x00000000,0x000007FF,
    0x00000000,0x00000FFF,0x00000000,0x00001FFF,0x00000000,0x00003FFF,0x00000000,0x00007FFF,
    0x00000000,0x0000FFFF,0x00000000,0x0001FFFF,0x00000000,0x0003FFFF,0x00000000,0x0007FFFF,
    0x00000000,0x000FFFFF,0x00000000,0x001FFFFF,0x00000000,0x003FFFFF,0x00000000,0x007FFFFF,
    0x00000000,0x00FFFFFF,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000007,
    0x0000000F,0x0000001F,0x0000003F,0x0000007F,0x000000FF,0x000001FF,0x000003FF,0x000007FF,
    0x00000FFF,0x00001FFF,0x00003FFF,0x00007FFF,0x0000FFFF,0x0001FFFF,0x0003FFFF,0x000FFFFF,
]


def _i32(b, o):
    return int.from_bytes(b[o:o + 4], 'little', signed=True)


def _u32(b, o):
    return int.from_bytes(b[o:o + 4], 'little', signed=False)


def _sub_8105E56C(result, a2, a3):
    if a3 > 63:
        result = 0
    elif a3 != 0:
        if a3 > 31:
            result = a2 >> (a3 - 32)
        else:
            result = ((a2 << (32 - a3)) | (result >> a3)) & 0xFFFFFFFF
    return result


def unpack_h(bp, out_size):
    """Huffman ('H').  out_size == the header's u32 unpacked_size."""
    buf = bytearray(0x10000)
    OFF2, OFF3, OFF4 = 0x2004, 0x2804, 0x3004
    cur_addr = 2
    next_pos = 2
    first_char = bp[0] if bp else 0
    idx1 = 0
    i1 = 0
    while True:  # build code tables from the 256-entry header
        pre_pos = next_pos
        cur_char1 = bp[cur_addr]
        next_addr = cur_addr + 1
        next_pos += 1
        if cur_char1 != 0:
            l1 = bp[cur_addr + 1]
            h1 = bp[cur_addr + 2]
            t1 = (l1 + (h1 << 8)) & 0xFFFF
            if cur_char1 >= 8:
                if cur_char1 >= 0xD:
                    if cur_char1 < 0x10:
                        d = t1
                        next_addr = cur_addr + 3
                        next_pos = pre_pos + 3
                    else:
                        d = t1 + (bp[cur_addr + 3] << 16)
                        next_addr = cur_addr + 4
                        next_pos = pre_pos + 4
                    buf[OFF3 + 4 + 8 * i1] = cur_char1 & 0xFF
                    buf[OFF3 + 8 * i1: OFF3 + 8 * i1 + 4] = struct.pack('<I', d & 0xFFFFFFFF)
                    buf[OFF3 + 5 + 8 * i1] = idx1 & 0xFF
                    i1 += 1
                else:
                    buf[2 * t1] = idx1 & 0xFF
                    buf[2 * t1 + 1] = cur_char1 & 0xFF
                    next_addr = cur_addr + 3
                    next_pos = pre_pos + 3
            else:
                buf[2 * l1] = idx1 & 0xFF
                buf[2 * l1 + 1] = cur_char1 & 0xFF
                next_addr = cur_addr + 2
                next_pos = pre_pos + 2
        cur_addr = next_addr
        idx1 += 1
        if idx1 == 0x100:
            break
    # buf2 (OFF2) <- buf3 (OFF3), bucketed by length; buf4 (OFF4) = start index per length
    idx2 = 0
    v19 = 0xD
    while True:
        i2 = 0
        buf[OFF4 + v19] = idx2 & 0xFF
        if i1 != 0:
            b3 = OFF3
            while True:
                if buf[b3 + 4] == v19:
                    buf[OFF2 + 8 * idx2: OFF2 + 8 * idx2 + 4] = bytes(buf[b3:b3 + 4])
                    buf[OFF2 + 4 + 8 * idx2: OFF2 + 8 + 8 * idx2] = bytes(buf[b3 + 4:b3 + 8])
                    idx2 += 1
                i2 += 1
                b3 += 8
                if i2 == i1:
                    break
        v19 += 1
        if v19 == 0x18:
            break
    buf[0x301c] = idx2 & 0xFF
    buf[0x3028:0x3030] = b'\x00' * 8

    output = bytearray(out_size)
    cur_output_addr = 0
    size_done = 0
    v33 = 0
    if out_size == 0:
        return b''
    while True:
        v24 = next_pos + ((v33 & 0x1F) >> 3) + ((v33 >> 3) & 0xFFFFFFFC)
        v25 = _u32(bp, v24)
        cur_char2 = first_char
        v27 = _sub_8105E56C(v25, 0, v33 & 7)
        outchar = None
        if first_char != 0xD:
            while True:
                v28 = v27 & MASK[2 * cur_char2]
                if cur_char2 == buf[2 * v28 + 1]:
                    outchar = buf[2 * v28]
                    break
                cur_char2 += 1
                if cur_char2 == 0xD:
                    break
        if outchar is None:  # long-code path (LABEL_22)
            if cur_char2 == 0x18:
                return bytes(output[:size_done])
            while True:
                v29 = buf[OFF4 + cur_char2]
                if v29 != buf[OFF4 + 1 + cur_char2]:
                    break
                cur_char2 += 1
                if cur_char2 == 0x18:
                    return bytes(output[:size_done])
            while _u32(buf, OFF2 + 8 * v29) != (v27 & MASK[2 * cur_char2]):
                v29 += 1
                if v29 == buf[OFF4 + 1 + cur_char2]:
                    cur_char2 += 1
                    if cur_char2 == 0x18:
                        return bytes(output[:size_done])
                    while True:  # LABEL_26_2
                        v29 = buf[OFF4 + cur_char2]
                        if v29 != buf[OFF4 + 1 + cur_char2]:
                            break
                        cur_char2 += 1
                        if cur_char2 == 0x18:
                            return bytes(output[:size_done])
            outchar = buf[OFF2 + 5 + 8 * v29]
        output[cur_output_addr] = outchar
        cur_output_addr += 1
        size_done += 1
        v33 += cur_char2
        if size_done >= out_size:
            return bytes(output)


def unpack_d(bp, out_size):
    """'D' codec (16-bit delta samples)."""
    output = bytearray(out_size)
    size1 = out_size >> 1
    if size1 == 0:
        return bytes(output)
    qword = 0
    i = 0
    cur_output_addr = 0
    v3 = 0
    while True:
        v6 = v3 & 0x1F
        v7 = (v3 >> 3) & 0xFFFFFFFC
        if (v3 & 0x1F) < 28:
            v8 = _i32(bp, v7)
        else:
            v8 = _i32(bp, v7 + 1)
            v6 -= 8
        v23 = v8 >> v6
        qword += 5
        v10 = qword & 0x1F
        idx = v23 & 0xF
        v11 = (qword >> 3) & 0xFFFFFFFC
        if v10 >= 24:
            v12 = _i32(bp, v11 + 3)
            v16 = v10 - 24
        elif v10 >= 16:
            v12 = _i32(bp, v11 + 2)
            v16 = v10 - 16
        else:
            if v10 < 8:
                v12 = _i32(bp, v11)
            else:
                v12 = _i32(bp, v11 + 1)
                v10 -= 8
            v16 = v10
        v19 = (D750[idx] & ((v12 >> v16) & 0xFFFFFFFF)) + D7A4[0x10 + idx]
        if (v23 & 0x10) != 0:
            v19 = (v19 & 0xFFFF0000) | ((~v19) & 0xFFFF)
        output[cur_output_addr] = v19 & 0xFF
        cur_output_addr += 1
        output[cur_output_addr] = (v19 >> 8) & 0xFF
        cur_output_addr += 1
        qword += D7A4[idx]
        i += 1
        v3 = qword
        if i == size1:
            break
    return bytes(output)


def unpack_r(data, out_size):
    """'R' run-length."""
    output = bytearray(out_size)
    p = 0
    dst = 0
    while dst < out_size:
        if p >= len(data):
            break
        ctl = data[p]
        p += 1
        if (ctl & 0xC0) == 0xC0:
            count = ctl & 0xF
            ctl &= 0xF0
        else:
            count = ctl & 0x3F
            ctl &= 0xC0
        if ctl == 0xF0:
            return bytes(output)
        elif ctl == 0x40:
            output[dst:dst + count] = data[p:p + count]
            p += count
            dst += count
        elif ctl == 0xD0:
            count = (count << 8) | data[p]
            p += 1
            output[dst:dst + count] = data[p:p + count]
            p += count
            dst += count
        elif ctl == 0x80:
            v = data[p]
            p += 1
            for _ in range(count):
                if dst < len(output):
                    output[dst] = v
                dst += 1
        elif ctl == 0xE0:
            count = (count << 8) | data[p]
            p += 1
            v = data[p]
            p += 1
            for _ in range(count):
                if dst < len(output):
                    output[dst] = v
                dst += 1
        elif ctl == 0x00:
            dst += count
        elif ctl == 0xC0:
            count = (count << 8) | data[p]
            p += 1
            dst += count
    return bytes(output)


def decrypt(data, enc):
    """Post-unpack 'enc' pass.  N=no-op, B=byte delta, W=LE word delta, S=BE word delta.
    The engine decodes in place, so the 'previous' value is the already-decoded one."""
    n = len(data)
    b = bytearray(data)
    if enc == 'N':
        return bytes(b)
    if enc == 'B':
        prev = 0
        for i in range(n):
            d = b[i]
            t = (-d) & 0xFF if i == 0 else (prev - d) & 0xFF
            b[i] = t
            prev = t
        return bytes(b)
    if enc == 'W':
        prev = 0
        for i in range(0, n - 1, 2):
            d = b[i] | (b[i + 1] << 8)
            t = (-d) & 0xFFFF if i == 0 else (prev - d) & 0xFFFF
            b[i] = t & 0xFF
            b[i + 1] = (t >> 8) & 0xFF
            prev = t
        return bytes(b)
    if enc == 'S':
        prev = 0
        for i in range(0, n - 1, 2):
            d = b[i + 1] | (b[i] << 8)  # big-endian word
            t = (-d) & 0xFFFF if i == 0 else (prev - d) & 0xFFFF
            b[i] = (t >> 8) & 0xFF
            b[i + 1] = t & 0xFF
            prev = t
        return bytes(b)
    return bytes(b)
