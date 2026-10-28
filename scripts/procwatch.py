# -*- coding: utf-8 -*-
"""实时监视进程内游戏文件的读取位置变化，定位"引擎刚刚读了哪一段"。

用法: python scripts/procwatch.py <pid> [秒数] [路径关键字]
输出: 位置变化的 (时间, 文件, 旧位置 -> 新位置)
"""
import ctypes as C
import sys
import time
from ctypes import wintypes as W

ntdll = C.windll.ntdll
k32 = C.windll.kernel32
SystemExtendedHandleInformation = 64
PROCESS_DUP_HANDLE = 0x0040
DUPLICATE_SAME_ACCESS = 0x00000002
FILE_CURRENT = 1


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
    dur = float(sys.argv[2]) if len(sys.argv) > 2 else 20
    kw = sys.argv[3] if len(sys.argv) > 3 else 'PCSG'
    h = k32.OpenProcess(PROCESS_DUP_HANDLE, False, pid)
    if not h:
        print('OpenProcess 失败 err=%d' % k32.GetLastError())
        return 2
    me = k32.GetCurrentProcess()
    watch = {}
    for hv in handles(pid):
        dup = W.HANDLE()
        if not k32.DuplicateHandle(C.c_void_p(h), C.c_void_p(hv), C.c_void_p(me),
                                   C.byref(dup), 0, False, DUPLICATE_SAME_ACCESS):
            continue
        buf = C.create_unicode_buffer(1024)
        ln = k32.GetFinalPathNameByHandleW(dup, buf, 1024, 0)
        if ln and kw.lower() in buf.value.lower():
            watch[dup.value] = [buf.value, pos_of(dup)]
        else:
            k32.CloseHandle(dup)
    print('监视 %d 个游戏文件句柄，%.0f 秒…' % (len(watch), dur))
    for k, v in watch.items():
        print('   %s  pos=%s' % (v[0].split('\\')[-1], v[1]))
    t0 = time.time()
    n = 0
    while time.time() - t0 < dur:
        for k, v in watch.items():
            p = pos_of(C.c_void_p(k))
            if p is not None and p != v[1]:
                print('  [%5.2fs] %s  %s -> %s' % (time.time() - t0, v[0].split('\\')[-1], v[1], p))
                v[1] = p
                n += 1
        time.sleep(0.02)
    print('变化 %d 次' % n)
    return 0


if __name__ == '__main__':
    sys.exit(main())
