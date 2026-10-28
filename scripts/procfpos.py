# -*- coding: utf-8 -*-
"""列出指定进程打开的游戏文件及其当前读写位置（GetFilePointer）。

句柄若被引擎保留（archive 常驻），指针位置就是"最近一次读取的结尾"，
据此可定位引擎刚刚读过哪个文件的哪一段。
用法: python scripts/procfpos.py <pid> [路径关键字]
"""
import ctypes as C
import sys
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


def main():
    pid = int(sys.argv[1])
    kw = sys.argv[2] if len(sys.argv) > 2 else ''
    h = k32.OpenProcess(PROCESS_DUP_HANDLE, False, pid)
    if not h:
        print('OpenProcess 失败 err=%d' % k32.GetLastError())
        return 2
    me = k32.GetCurrentProcess()
    rows = []
    for hv in handles(pid):
        dup = W.HANDLE()
        if not k32.DuplicateHandle(C.c_void_p(h), C.c_void_p(hv), C.c_void_p(me),
                                   C.byref(dup), 0, False, DUPLICATE_SAME_ACCESS):
            continue
        buf = C.create_unicode_buffer(1024)
        ln = k32.GetFinalPathNameByHandleW(dup, buf, 1024, 0)
        pos = None
        if ln:
            lo = k32.SetFilePointer(dup, 0, None, FILE_CURRENT)
            hi = W.LONG(0)
            if lo != 0xFFFFFFFF:
                lo2 = k32.SetFilePointer(dup, 0, C.byref(hi), FILE_CURRENT)
                pos = (hi.value << 32) | (lo2 & 0xFFFFFFFF)
        k32.CloseHandle(dup)
        if ln and pos is not None:
            rows.append((buf.value, pos))
    seen = {}
    for p, pos in rows:
        seen.setdefault(p, set()).add(pos)
    print('可定位文件 %d 个：' % len(seen))
    for p in sorted(seen):
        if kw and kw.lower() not in p.lower():
            continue
        print('  pos=%s  %s' % (','.join(str(x) for x in sorted(seen[p])), p))
    return 0


if __name__ == '__main__':
    sys.exit(main())
