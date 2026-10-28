# -*- coding: utf-8 -*-
"""列出指定进程当前打开的文件路径。

做法: NtQuerySystemInformation(SystemExtendedHandleInformation) 遍历句柄 →
DuplicateHandle 到本进程 → GetFinalPathNameByHandleW 取路径（非文件句柄会直接失败，不会卡住）。
用法: python scripts/prochandles.py <pid>
"""
import ctypes as C
import sys
from ctypes import wintypes as W

ntdll = C.windll.ntdll
k32 = C.windll.kernel32

SystemExtendedHandleInformation = 64
PROCESS_DUP_HANDLE = 0x0040
DUPLICATE_SAME_ACCESS = 0x00000002


class SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX(C.Structure):
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
        need = ret.value + (1 << 16)          # STATUS_INFO_LENGTH_MISMATCH 时 ret 给所需长度
        size = max(size * 2, need)
    else:
        return []
    cnt = C.cast(buf, C.POINTER(C.c_ulonglong))[0]
    arr = C.cast(C.addressof(buf) + 16, C.POINTER(SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX))
    out = []
    for i in range(cnt):
        e = arr[i]
        if (e.UniqueProcessId or 0) == pid:
            out.append((e.HandleValue or 0, e.ObjectTypeIndex, e.GrantedAccess))
    return out


def main():
    pid = int(sys.argv[1])
    h = k32.OpenProcess(PROCESS_DUP_HANDLE, False, pid)
    if not h:
        print('OpenProcess(DUP_HANDLE) 失败 err=%d' % k32.GetLastError())
        return 2
    me = k32.GetCurrentProcess()
    paths = {}
    n = 0
    for hv, ti, ga in handles(pid):
        n += 1
        dup = W.HANDLE()
        if not k32.DuplicateHandle(C.c_void_p(h), C.c_void_p(hv), C.c_void_p(me),
                                   C.byref(dup), 0, False, DUPLICATE_SAME_ACCESS):
            continue
        buf = C.create_unicode_buffer(1024)
        ln = k32.GetFinalPathNameByHandleW(dup, buf, 1024, 0)
        k32.CloseHandle(dup)
        if ln and ln < 1024:
            p = buf.value
            paths[p] = paths.get(p, 0) + 1
    print('句柄总数 %d，可解析为文件路径 %d 个：' % (n, len(paths)))
    for p in sorted(paths):
        print('  ', p)
    return 0


if __name__ == '__main__':
    sys.exit(main())
