# -*- coding: utf-8 -*-
"""遍历进程内指定 guest 地址区间的已提交区域，就地提取 cp932 日文段落。

Vita3K 把 guest 内存映射在 host 0x400000000 起，guest 地址 = host - 0x400000000。
用法: python scripts/memtext.py <pid> <guest_start_hex> <guest_end_hex> [最多打印条数]
输出: guest 地址 + 文本（按\"像正文\"程度排序）
"""
import ctypes as C
import re
import sys
from ctypes import wintypes as W

k32 = C.windll.kernel32
k32.OpenProcess.restype = W.HANDLE
HOST = 0x400000000
RUN = re.compile(rb'(?:[\x81-\x9f\xe0-\xfc][\x40-\xfc]){4,}')


class MBI(C.Structure):
    _fields_ = [('BaseAddress', C.c_ulonglong), ('AllocationBase', C.c_ulonglong),
                ('AllocationProtect', W.DWORD), ('__a1', W.DWORD),
                ('RegionSize', C.c_ulonglong), ('State', W.DWORD),
                ('Protect', W.DWORD), ('Type', W.DWORD), ('__a2', W.DWORD)]


def main():
    pid = int(sys.argv[1], 0)
    g0 = int(sys.argv[2], 0)
    g1 = int(sys.argv[3], 0)
    limit = int(sys.argv[4]) if len(sys.argv) > 4 else 40
    h = k32.OpenProcess(0x0410, False, pid)
    if not h:
        print('OpenProcess 失败 err=%d' % k32.GetLastError())
        return 2
    mbi = MBI()
    sz = C.sizeof(mbi)
    addr = HOST + g0
    found = []
    read_b = 0
    CHUNK = 2 << 20
    while addr < HOST + g1 and k32.VirtualQueryEx(h, C.c_void_p(addr), C.byref(mbi), sz) == sz:
        size = mbi.RegionSize
        nxt = mbi.BaseAddress + size
        if mbi.State == 0x1000 and not (mbi.Protect & 0x101):
            off = 0
            while off < size:
                n = min(CHUNK, size - off)
                buf = C.create_string_buffer(n)
                got = C.c_size_t(0)
                if k32.ReadProcessMemory(h, C.c_void_p(mbi.BaseAddress + off), buf, n, C.byref(got)) and got.value:
                    b = buf.raw[:got.value]
                    read_b += len(b)
                    gbase = mbi.BaseAddress + off - HOST
                    for m in RUN.finditer(b):
                        try:
                            s = m.group().decode('cp932')
                        except Exception:
                            continue
                        hira = len(re.findall(r'[ぁ-ん]', s))
                        if hira < 3 or not re.search(r'[、。！？…」』]', s):
                            continue
                        found.append((gbase + m.start(), s))
                off += n
        if nxt <= addr:
            break
        addr = nxt
    print('读 %.1f MB，疑似正文段 %d' % (read_b / 1048576, len(found)))
    # 按\"像正文\"程度排序：平假名比例高、含标点、长度适中
    def score(t):
        hira = len(re.findall(r'[ぁ-ん]', t))
        return (hira / max(1, len(t))) * min(len(t), 60)
    found.sort(key=lambda x: -score(x[1]))
    for a, s in found[:limit]:
        print(f'  0x{a:08X} {s[:80]!r}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
