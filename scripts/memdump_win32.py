#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从**正在运行**的 32 位游戏进程里按绝对地址读内存并 dump（不启动游戏）。

用法：
  python scripts/memdump_win32.py --proc VAMPIRESWEETIE.exe \
      --read 0x4f6cb4:0x400 --read 0x6d365f:0x200 --read 0x6d365f+0x10a4:0x200 \
      --read 0x6d34a0:4 --out _work_vs/memdump.txt

地址写法：
  0xADDR:SIZE            直接读
  0xBASE+i*STRIDE:SIZE   循环读（i 自动 0..--count-1，需同时给 --count/--stride）
  0xBASE+N:4             BASE+N 也支持
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import re
import sys

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010


class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [('dwSize', wt.DWORD), ('cntUsage', wt.DWORD),
                ('th32ProcessID', wt.DWORD), ('th32DefaultHeapID', ctypes.POINTER(ctypes.c_ulong)),
                ('th32ModuleID', wt.DWORD), ('cntThreads', wt.DWORD),
                ('th32ParentProcessID', wt.DWORD), ('pcPriClassBase', ctypes.c_long),
                ('dwFlags', wt.DWORD), ('szExeFile', ctypes.c_char * 260)]


def find_pids(name):
    snap = k32.CreateToolhelp32Snapshot(0x00000002, 0)
    if snap == -1:
        return []
    pe = PROCESSENTRY32()
    pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
    out = []
    ok = k32.Process32First(snap, ctypes.byref(pe))
    while ok:
        if pe.szExeFile.decode('mbcs', 'replace').lower() == name.lower():
            out.append(pe.th32ProcessID)
        ok = k32.Process32Next(snap, ctypes.byref(pe))
    k32.CloseHandle(snap)
    return out


def read(h, addr, size):
    buf = ctypes.create_string_buffer(size)
    n = ctypes.c_size_t(0)
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, ctypes.byref(n)):
        return None
    return buf.raw[:n.value]


def parse(spec, count, stride):
    m = re.match(r'^(0x[0-9a-fA-F]+)(?:\+(\d+))?$', spec)
    if not m:
        raise SystemExit('地址写错: %r' % spec)
    base = int(m.group(1), 16)
    if m.group(2):
        base += int(m.group(2))
    return [(base + i * stride, i) for i in range(count)] if stride else [(base, 0)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--proc', required=True)
    ap.add_argument('--read', action='append', required=True)
    ap.add_argument('--count', type=int, default=8)
    ap.add_argument('--stride', type=lambda s: int(s, 0), default=0)
    ap.add_argument('--out')
    a = ap.parse_args()

    pids = find_pids(a.proc)
    if not pids:
        print('进程未运行: %s —— 先启动游戏再看' % a.proc)
        return 2
    pid = pids[0]
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        print('OpenProcess 失败 pid=%d err=%d（试试管理员权限）' % (pid, ctypes.get_last_error()))
        return 3
    print('# pid=%d  %s' % (pid, a.proc))
    lines = []
    for spec in a.read:
        addr, size = spec.split(':') if ':' in spec else (spec, '4')
        size = int(size, 0)
        for ad, idx in parse(addr, a.count, a.stride):
            data = read(h, ad, size)
            if data is None:
                lines.append('%08x #%d  <读失败>' % (ad, idx))
                continue
            try:
                txt = data.split(b'\x00')[0].decode('cp932')
            except UnicodeDecodeError:
                txt = data.split(b'\x00')[0].decode('cp932', 'replace')
            lines.append('%08x #%d  %s' % (ad, idx, txt.replace('\n', '\\n')))
            lines.append('    hex %s' % data.hex(' '))
    k32.CloseHandle(h)
    txt = '\n'.join(lines)
    if a.out:
        open(a.out, 'w', encoding='utf-8', newline='\n').write(txt + '\n')
        print('written %s (%d lines)' % (a.out, len(lines)))
    else:
        print(txt)
    return 0


if __name__ == '__main__':
    sys.exit(main())
