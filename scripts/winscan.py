"""Windows 进程内存扫描器：定位指定进程里 cp932 日文正文最密集的区域并导出。

用途：模拟器（Eden / Yuzu / Vita3K 等）运行时，引擎把压缩脚本解压到堆里，
      直接从内存整块 dump 比反推压缩算法快得多。

用法：
    python scripts/winscan.py <pid>                    # 只统计，不落盘
    python scripts/winscan.py <pid> --dump DIR         # 把密集区导出为 DIR/region_XXXX.bin
    python scripts/winscan.py <pid> --needle それは絶対 # 只找含该串的区域
"""
import ctypes as C
import os
import re
import sys
from ctypes import wintypes as W

k32 = C.windll.kernel32
k32.OpenProcess.restype = W.HANDLE

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01


class MBI(C.Structure):
    _fields_ = [('BaseAddress', C.c_ulonglong), ('AllocationBase', C.c_ulonglong),
                ('AllocationProtect', W.DWORD), ('__a1', W.DWORD),
                ('RegionSize', C.c_ulonglong), ('State', W.DWORD),
                ('Protect', W.DWORD), ('Type', W.DWORD), ('__a2', W.DWORD)]


JP = re.compile(rb'(?:[\x81-\x9f\xe0-\xfc][\x40-\xfc]){10,}')
HIRA = re.compile(r'[ぁ-ん]')


def jp_runs(blk):
    out = []
    for m in JP.finditer(blk):
        try:
            s = m.group().decode('cp932')
        except Exception:
            continue
        if len(HIRA.findall(s)) >= 5:
            out.append((m.start(), s))
    return out


def regions(h):
    addr = 0
    mbi = MBI()
    size = C.sizeof(mbi)
    while k32.VirtualQueryEx(h, C.c_void_p(addr), C.byref(mbi), size) == size:
        if (mbi.State == MEM_COMMIT and mbi.RegionSize
                and not (mbi.Protect & PAGE_GUARD)
                and (mbi.Protect & 0xFF) != PAGE_NOACCESS):
            yield mbi.BaseAddress, mbi.RegionSize
        nxt = mbi.BaseAddress + mbi.RegionSize
        if nxt <= addr:
            break
        addr = nxt


def read(h, addr, n):
    buf = C.create_string_buffer(n)
    got = C.c_size_t(0)
    ok = k32.ReadProcessMemory(h, C.c_void_p(addr), buf, n, C.byref(got))
    return buf.raw[:got.value] if ok else b''


def main():
    pid = int(sys.argv[1])
    dumpdir = None
    needle = None
    if '--dump' in sys.argv:
        dumpdir = sys.argv[sys.argv.index('--dump') + 1]
        os.makedirs(dumpdir, exist_ok=True)
    if '--needle' in sys.argv:
        needle = sys.argv[sys.argv.index('--needle') + 1].encode('cp932')

    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        print('OpenProcess 失败')
        return 1

    CH = 8 << 20
    rows = []
    for base, size in regions(h):
        for off in range(0, size, CH):
            n = min(CH, size - off)
            blk = read(h, base + off, n)
            if len(blk) < 4096:
                continue
            if needle is not None and needle not in blk:
                continue
            runs = jp_runs(blk)
            if runs:
                rows.append((len(runs), base + off, len(blk), runs))
    rows.sort(reverse=True)
    print(f'进程 {pid}: 命中块 {len(rows)}')
    for cnt, addr, ln, runs in rows[:10]:
        print(f'  0x{addr:012X}  {ln/1048576:.1f}MB  日文段 {cnt}  例: {runs[0][1][:40]!r}')
    if dumpdir:
        for cnt, addr, ln, runs in rows[:20]:
            data = read(h, addr, ln)
            with open(os.path.join(dumpdir, f'region_{addr:012X}.bin'), 'wb') as f:
                f.write(data)
        print('已导出前 20 块到', dumpdir)
    return 0


if __name__ == '__main__':
    sys.exit(main())
