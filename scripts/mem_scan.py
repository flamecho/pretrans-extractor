#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取运行中进程的内存，按编码搜日文串（用于「格式解不开时，直接从运行时抓明文」）。

用法:
  python scripts/mem_scan.py <pid> --needle レティシア
  python scripts/mem_scan.py <pid> --dump-jp out.txt [--min 8] [--limit 200000]

要点：
  * Unity 的 C# string 在内存里是 **UTF-16LE**；也有 UTF-8（原生 char*）与 Shift-JIS 变体，
    三种都扫，命中时打印编码。
  * 只扫 MEM_COMMIT 且可读的私有/映射区（跳过 IMAGE 段外的保留区），单区 >256MB 跳过。
"""
import argparse
import ctypes
import ctypes.wintypes as w
import re
import sys

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
READABLE = (0x02, 0x04, 0x20, 0x40, 0x80)
CHUNK = 1 << 20


class MBI(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_ulonglong), ('AllocationBase', ctypes.c_ulonglong),
                ('AllocationProtect', w.DWORD), ('__a1', w.DWORD), ('RegionSize', ctypes.c_ulonglong),
                ('State', w.DWORD), ('Protect', w.DWORD), ('Type', w.DWORD), ('__a2', w.DWORD)]


def open_proc(pid):
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        raise SystemExit('OpenProcess 失败 err=%d（需与目标同权限，管理员进程要管理员运行）'
                         % ctypes.get_last_error())
    return h


def regions(h, max_region=256 << 20):
    k32.VirtualQueryEx.argtypes = [w.HANDLE, ctypes.c_ulonglong, ctypes.POINTER(MBI), ctypes.c_size_t]
    addr, out = 0, []
    while addr < 0x7FFFFFFFFFFF:
        mbi = MBI()
        if not k32.VirtualQueryEx(h, addr, ctypes.byref(mbi), ctypes.sizeof(mbi)):
            break
        if mbi.State == MEM_COMMIT and mbi.Protect in READABLE and 0 < mbi.RegionSize < max_region:
            out.append((mbi.BaseAddress, mbi.RegionSize))
        addr = mbi.BaseAddress + mbi.RegionSize
    return out


def iter_blocks(h, regs):
    buf = ctypes.create_string_buffer(CHUNK)
    read = ctypes.c_size_t(0)
    k32.ReadProcessMemory.argtypes = [w.HANDLE, ctypes.c_ulonglong, ctypes.c_void_p,
                                      ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    k32.ReadProcessMemory.restype = w.BOOL
    for base, size in regs:
        p = base
        while p < base + size:
            n = min(CHUNK, base + size - p)
            if k32.ReadProcessMemory(h, p, buf, n, ctypes.byref(read)) and read.value:
                yield p, buf.raw[:read.value]
            p += n


JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff\u3005\u30fc]')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pid', type=int)
    ap.add_argument('--needle')
    ap.add_argument('--dump-jp')
    ap.add_argument('--min', type=int, default=8)
    ap.add_argument('--limit', type=int, default=200000)
    ap.add_argument('--ctx', type=int, default=60)
    a = ap.parse_args()
    h = open_proc(a.pid)
    regs = regions(h)
    print('[i] 可读区 %d 个 / %d MB' % (len(regs), sum(r[1] for r in regs) >> 20), file=sys.stderr)

    if a.needle:
        encs = [('utf-16-le', a.needle.encode('utf-16-le')),
                ('utf-8', a.needle.encode('utf-8')),
                ('cp932', a.needle.encode('cp932', 'ignore'))]
        n = 0
        for base, data in iter_blocks(h, regs):
            for name, nb in encs:
                i = data.find(nb)
                while i >= 0 and n < 20:
                    s = max(0, i - a.ctx * 2)
                    seg = data[s:i + a.ctx * 2]
                    try:
                        txt = seg.decode(name, 'replace')
                    except Exception:
                        txt = repr(seg)
                    print('[hit] %#x %-9s %s' % (base + i, name, txt.replace('\n', '⏎')))
                    n += 1
                    i = data.find(nb, i + 1)
        print('[i] 命中 %d' % n)
        return

    # 全量 dump 日文串
    seen = set()
    out = []
    for base, data in iter_blocks(h, regs):
        for name in ('utf-16-le', 'utf-8', 'cp932'):
            step = 2 if name == 'utf-16-le' else 1
            for m in re.finditer(rb'(?:..){%d,}' % a.min if step == 2 else rb'.{%d,}' % a.min,
                                 data, re.S):
                raw = m.group()
                try:
                    s = raw.decode(name)
                except Exception:
                    continue
                if not JP.search(s):
                    continue
                k_ = sum(1 for c in s if JP.match(c))
                if k_ / max(1, len(s)) < 0.6:
                    continue
                t = s.strip()
                if t in seen:
                    continue
                seen.add(t)
                out.append(t)
                if len(out) >= a.limit:
                    break
    print('[i] 提取 %d 条' % len(out), file=sys.stderr)
    if a.dump_jp:
        with open(a.dump_jp, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(out) + '\n')
        print('[ok]', a.dump_jp)


if __name__ == '__main__':
    main()
