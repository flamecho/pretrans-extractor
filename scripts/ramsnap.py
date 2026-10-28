# -*- coding: utf-8 -*-
"""把 guest 内存整段 dump 到文件（分块读，支持 100MB 级区域）。

用法: python scripts/ramsnap.py <pid> <guest_start_hex> <guest_end_hex> <out_file>
"""
import ctypes as C
import sys
from ctypes import wintypes as W

k32 = C.windll.kernel32
k32.OpenProcess.restype = W.HANDLE
HOST = 0x400000000


def main():
    pid = int(sys.argv[1], 0)
    g0 = int(sys.argv[2], 0)
    g1 = int(sys.argv[3], 0)
    out = sys.argv[4]
    h = k32.OpenProcess(0x0410, False, pid)
    if not h:
        print('OpenProcess 失败')
        return 2
    CH = 4 << 20
    total = 0
    with open(out, 'wb') as f:
        g = g0
        while g < g1:
            n = min(CH, g1 - g)
            b = C.create_string_buffer(n)
            got = C.c_size_t(0)
            if k32.ReadProcessMemory(h, C.c_void_p(HOST + g), b, n, C.byref(got)) and got.value:
                f.write(b.raw[:got.value])
                total += got.value
            else:
                f.write(b'\x00' * n)
            g += n
    print('dump %d B -> %s' % (total, out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
