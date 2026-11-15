"""Windows 进程内存导出（只读，用于从运行中的游戏抓明文）。

用法：
    python scripts/win_memdump.py <pid> <out.bin>
输出：单一转储文件 + 同名 .map.tsv（每段 region 的基址/大小/保护）
说明：只导出 MEM_COMMIT 且可读的 region；跳过 >256MB 的单段。
"""
import ctypes
import ctypes.wintypes as wt
import struct
import sys

k32 = ctypes.WinDLL('kernel32', use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01
READABLE = (0x02, 0x04, 0x08, 0x20, 0x40, 0x80)   # READONLY/READWRITE/WRITECOPY/EXECUTE_READ...


class MEMORY_BASIC_INFORMATION64(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_ulonglong),
                ('AllocationBase', ctypes.c_ulonglong),
                ('AllocationProtect', wt.DWORD),
                ('__alignment1', wt.DWORD),
                ('RegionSize', ctypes.c_ulonglong),
                ('State', wt.DWORD),
                ('Protect', wt.DWORD),
                ('Type', wt.DWORD),
                ('__alignment2', wt.DWORD)]


def main():
    pid = int(sys.argv[1])
    out = sys.argv[2]
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        raise SystemExit('OpenProcess failed: %d' % ctypes.get_last_error())
    addr = 0
    mbi = MEMORY_BASIC_INFORMATION64()
    rows = []
    total = 0
    with open(out, 'wb') as f, open(out + '.map.tsv', 'w', encoding='utf-8') as m:
        m.write('dump_off\tbase\tsize\tprotect\ttype\n')
        while addr < 0x7FFFFFFF0000:
            got = k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi))
            if not got:
                break
            base, size = mbi.BaseAddress, mbi.RegionSize
            if (mbi.State == MEM_COMMIT and mbi.Protect not in (PAGE_NOACCESS,)
                    and not (mbi.Protect & PAGE_GUARD) and size <= 256 << 20):
                buf = ctypes.create_string_buffer(size)
                n = ctypes.c_size_t(0)
                if k32.ReadProcessMemory(h, ctypes.c_void_p(base), buf,
                                         ctypes.c_size_t(size), ctypes.byref(n)):
                    f.write(buf.raw[:n.value])
                    m.write('%d\t%d\t%d\t%#x\t%#x\n' % (total, base, n.value, mbi.Protect, mbi.Type))
                    total += n.value
            addr = base + size
    k32.CloseHandle(h)
    print('dumped %d bytes -> %s' % (total, out))


if __name__ == '__main__':
    main()
