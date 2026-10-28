# -*- coding: utf-8 -*-
"""扫描另一个进程的内存，按多种编码查找关键词（用于判断某段文本在运行时是否以明文存在）。

用法: python scripts/memscan.py <pid> <关键词1> [关键词2 ...]
输出: 命中地址 + 前后上下文；并自动判断该区域是否为大段连续日文（说明是整块载入的文本表）
"""
import ctypes as C
import sys
from ctypes import wintypes as W

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01

k32 = C.windll.kernel32
k32.OpenProcess.restype = W.HANDLE


class MEMORY_BASIC_INFORMATION64(C.Structure):
    _fields_ = [
        ('BaseAddress', C.c_ulonglong),
        ('AllocationBase', C.c_ulonglong),
        ('AllocationProtect', W.DWORD),
        ('__alignment1', W.DWORD),
        ('RegionSize', C.c_ulonglong),
        ('State', W.DWORD),
        ('Protect', W.DWORD),
        ('Type', W.DWORD),
        ('__alignment2', W.DWORD),
    ]


def regions(h):
    addr = 0
    mbi = MEMORY_BASIC_INFORMATION64()
    sz = C.sizeof(mbi)
    while k32.VirtualQueryEx(h, C.c_void_p(addr), C.byref(mbi), sz) == sz:
        yield mbi
        nxt = mbi.BaseAddress + mbi.RegionSize
        if nxt <= addr:
            break
        addr = nxt


def read(h, addr, n):
    buf = C.create_string_buffer(n)
    got = C.c_size_t(0)
    ok = k32.ReadProcessMemory(h, C.c_void_p(addr), buf, n, C.byref(got))
    if not ok or got.value == 0:
        return None
    return buf.raw[:got.value]


def enc_variants(s):
    out = {}
    for enc in ('utf-8', 'utf-16-le', 'utf-16-be', 'cp932'):
        try:
            out[enc] = s.encode(enc)
        except Exception:
            pass
    return out


def is_jp(b):
    """粗略判断字节块内日文密度（UTF-8 三字节 / UTF-16 假名区）"""
    if not b:
        return 0
    t = b.decode('utf-8', 'ignore')
    jp = sum(1 for c in t if '\u3040' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff')
    return jp / max(1, len(t))


def main():
    pid = int(sys.argv[1])
    needles = sys.argv[2:]
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        print('OpenProcess 失败 err=%d（需管理员权限？）' % k32.GetLastError())
        return 2
    print('已打开 PID %d' % pid)
    targets = [(s, enc, nb) for s in needles for enc, nb in enc_variants(s).items()]

    total_regions = 0
    scanned = 0
    hits = []
    CHUNK = 4 << 20
    for mbi in regions(h):
        if mbi.State != MEM_COMMIT:
            continue
        total_regions += 1
        if mbi.Protect & (PAGE_GUARD | PAGE_NOACCESS):
            continue
        base, size = mbi.BaseAddress, mbi.RegionSize
        if size > (1 << 32):
            continue
        off = 0
        while off < size:
            n = min(CHUNK, size - off)
            buf = read(h, base + off, n)
            if buf:
                scanned += n
                for s, enc, nb in targets:
                    p = buf.find(nb)
                    while p >= 0:
                        hits.append((s, enc, base + off + p))
                        p = buf.find(nb, p + 1)
            off += n
    print('区域 %d，已读 %.1f MB，命中 %d' % (total_regions, scanned / 1048576, len(hits)))
    for s, enc, a in hits:
        print('\n=== %r [%s] @ 0x%X ===' % (s, enc, a))
        ctx = read(h, max(0, a - 320), 900)
        if ctx:
            dec = ctx.decode('utf-8' if enc.startswith('utf-8') else ('utf-16-le' if enc == 'utf-16-le' else ('cp932' if enc == 'cp932' else 'utf-16-be')), 'replace')
            print('  日文密度 %.2f' % is_jp(ctx))
            print('  ' + dec.replace('\x00', '·')[:600])
    return 0


if __name__ == '__main__':
    sys.exit(main())
