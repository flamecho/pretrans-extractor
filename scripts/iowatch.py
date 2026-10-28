# -*- coding: utf-8 -*-
"""按秒采样进程 I/O 计数与文本槽变化，定位"一次点击读了多少字节、出现哪些新文本"。

用法: python scripts/iowatch.py <pid> <秒数>
"""
import ctypes as C
import re
import struct
import sys
import time
from ctypes import wintypes as W

k32 = C.windll.kernel32
k32.OpenProcess.restype = W.HANDLE
HOST = 0x400000000


class IOC(C.Structure):
    _fields_ = [('ReadOperationCount', C.c_ulonglong), ('WriteOperationCount', C.c_ulonglong),
                ('OtherOperationCount', C.c_ulonglong), ('ReadTransferCount', C.c_ulonglong),
                ('WriteTransferCount', C.c_ulonglong), ('OtherTransferCount', C.c_ulonglong)]


def main():
    pid = int(sys.argv[1])
    dur = float(sys.argv[2]) if len(sys.argv) > 2 else 60
    hq = k32.OpenProcess(0x0400, False, pid)
    hv = k32.OpenProcess(0x0410, False, pid)
    if not hq or not hv:
        print('OpenProcess 失败')
        return 2

    def read(g, n):
        b = C.create_string_buffer(n)
        got = C.c_size_t(0)
        if k32.ReadProcessMemory(hv, C.c_void_p(HOST + g), b, n, C.byref(got)) and got.value:
            return b.raw[:got.value]
        return b''

    io = IOC()
    k32.GetProcessIoCounters(C.c_void_p(hq), C.byref(io))
    prev_r, prev_n = io.ReadTransferCount, io.ReadOperationCount
    base, N = 0x8114AA88, 0x280 * 40
    seen = read(base, N)
    print('起始：读 %d B / %d 次' % (prev_r, prev_n), flush=True)
    t0 = time.time()
    while time.time() - t0 < dur:
        time.sleep(0.03)
        k32.GetProcessIoCounters(C.c_void_p(hq), C.byref(io))
        d = io.ReadTransferCount - prev_r
        if d > 0:
            print('  [%5.2fs] 磁盘读 +%d B（%d 次）' % (time.time() - t0, d, io.ReadOperationCount - prev_n), flush=True)
            prev_r, prev_n = io.ReadTransferCount, io.ReadOperationCount
        cur = read(base, N)
        if len(cur) == len(seen) and cur != seen:
            for i in range(0, N, 0x280):
                if cur[i:i + 0x280] == seen[i:i + 0x280]:
                    continue
                sid, li = struct.unpack_from('<II', cur, i)
                ln = struct.unpack_from('<I', cur, i + 0x14)[0]
                if 0 < ln < 400:
                    try:
                        t = cur[i + 0x20:i + 0x20 + ln * 2].decode('cp932')
                    except Exception:
                        t = '?'
                    print('  [%5.2fs] 槽%2d 写入 sid=%d line=%d：%r' % (time.time() - t0, i // 0x280, sid, li, t[:50]), flush=True)
            seen = cur
    print('结束')
    return 0


if __name__ == '__main__':
    sys.exit(main())
