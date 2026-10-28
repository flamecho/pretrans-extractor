# -*- coding: utf-8 -*-
"""联合监视：游戏文件读取位置变化 + guest 堆中新出现的 cp932 日文串。

用法: python scripts/procboth.py <pid> <秒数>
说明: 运行期间在游戏里点击推进文本，即可看清"每点一次"读了哪个文件的哪一段、
      以及新文本出现在内存哪个地址。
"""
import ctypes as C
import re
import sys
import time
from ctypes import wintypes as W

ntdll = C.windll.ntdll
k32 = C.windll.kernel32
SystemExtendedHandleInformation = 64
PROCESS_DUP_HANDLE = 0x0040
DUPLICATE_SAME_ACCESS = 0x00000002
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
FILE_CURRENT = 1
HOST = 0x400000000
RUN = re.compile(rb'(?:[\x81-\x9f\xe0-\xfc][\x40-\xfc]){6,}')


class ENTRY(C.Structure):
    _fields_ = [('Object', C.c_void_p), ('UniqueProcessId', C.c_void_p),
                ('HandleValue', C.c_void_p), ('GrantedAccess', W.DWORD),
                ('CreatorBackTraceIndex', W.WORD), ('ObjectTypeIndex', W.WORD),
                ('HandleAttributes', W.DWORD), ('Reserved', W.DWORD)]


def handles(pid):
    size = 1 << 22
    for _ in range(6):
        buf = C.create_string_buffer(size)
        ret = C.c_ulong(0)
        st = ntdll.NtQuerySystemInformation(SystemExtendedHandleInformation, buf, size, C.byref(ret))
        if st == 0:
            break
        size = max(size * 2, ret.value + (1 << 16))
    else:
        return []
    cnt = C.cast(buf, C.POINTER(C.c_ulonglong))[0]
    arr = C.cast(C.addressof(buf) + 16, C.POINTER(ENTRY))
    return [(e.HandleValue or 0) for i in range(cnt)
            for e in [arr[i]] if (e.UniqueProcessId or 0) == pid]


def pos_of(h):
    lo = k32.SetFilePointer(h, 0, None, FILE_CURRENT)
    if lo == 0xFFFFFFFF:
        return None
    hi = W.LONG(0)
    lo2 = k32.SetFilePointer(h, 0, C.byref(hi), FILE_CURRENT)
    return (hi.value << 32) | (lo2 & 0xFFFFFFFF)


def main():
    pid = int(sys.argv[1])
    dur = float(sys.argv[2]) if len(sys.argv) > 2 else 60
    hd = k32.OpenProcess(PROCESS_DUP_HANDLE, False, pid)
    hv = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not hd or not hv:
        print('OpenProcess 失败')
        return 2
    me = k32.GetCurrentProcess()
    watch = {}
    for hv_ in handles(pid):
        dup = W.HANDLE()
        if not k32.DuplicateHandle(C.c_void_p(hd), C.c_void_p(hv_), C.c_void_p(me),
                                   C.byref(dup), 0, False, DUPLICATE_SAME_ACCESS):
            continue
        buf = C.create_unicode_buffer(1024)
        ln = k32.GetFinalPathNameByHandleW(dup, buf, 1024, 0)
        if ln and 'PCSG' in buf.value:
            watch[dup.value] = [buf.value.split('\\')[-1], pos_of(dup)]
        else:
            k32.CloseHandle(dup)
    print('监视 %d 个文件 + 堆文本' % len(watch), flush=True)

    def read(g, n):
        b = C.create_string_buffer(n)
        got = C.c_size_t(0)
        if k32.ReadProcessMemory(hv, C.c_void_p(HOST + g), b, n, C.byref(got)) and got.value:
            return b.raw[:got.value]
        return b''

    G0, G1 = 0x81100000, 0x81500000
    seen = set()
    base = read(G0, G1 - G0)
    for m in RUN.finditer(base):
        seen.add((m.start(), m.group()[:24]))
    print('初始已见日文串 %d 个' % len(seen), flush=True)
    t0 = time.time()
    while time.time() - t0 < dur:
        for k, v in watch.items():
            p = pos_of(C.c_void_p(k))
            if p is not None and p != v[1]:
                print('  [%5.2fs] 文件 %s  %s -> %s' % (time.time() - t0, v[0], v[1], p), flush=True)
                v[1] = p
        cur = read(G0, G1 - G0)
        new = 0
        for m in RUN.finditer(cur):
            key = (m.start(), m.group()[:24])
            if key in seen:
                continue
            seen.add(key)
            try:
                t = m.group().decode('cp932')
            except Exception:
                continue
            if not re.search(r'[ぁ-ん]{2,}', t):
                continue
            print('  [%5.2fs] 新文本 @guest=0x%08X  %r' % (time.time() - t0, G0 + m.start(), t[:60]), flush=True)
            new += 1
        time.sleep(0.1)
    print('结束')
    return 0


if __name__ == '__main__':
    sys.exit(main())
