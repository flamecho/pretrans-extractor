# -*- coding: utf-8 -*-
"""从进程内存 dump 一段区间到文件。用法: python scripts/memdump.py <pid> <hex_addr> <size> <out>"""
import ctypes as C
import sys
from ctypes import wintypes as W

k32 = C.windll.kernel32
k32.OpenProcess.restype = W.HANDLE


def main():
    pid = int(sys.argv[1], 0)
    addr = int(sys.argv[2], 0)
    size = int(sys.argv[3], 0)
    out = sys.argv[4]
    h = k32.OpenProcess(0x0410, False, pid)
    if not h:
        print('OpenProcess 失败 err=%d' % k32.GetLastError())
        return 2
    buf = C.create_string_buffer(size)
    got = C.c_size_t(0)
    ok = k32.ReadProcessMemory(h, C.c_void_p(addr), buf, size, C.byref(got))
    data = buf.raw[:got.value]
    open(out, 'wb').write(data)
    print('dump %d B -> %s (ok=%s)' % (len(data), out, ok))
    return 0


if __name__ == '__main__':
    sys.exit(main())
