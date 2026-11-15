#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从运行中的进程内存里捞 CP932 日文（PC 游戯 文本提取的「运行时」路线）

用途：脚本被加密/自有压缩、静态解不开，但游戯运行时会解到内存 ⇒ 直接读明文。
（首次用：2026-10-30 クレイジー★ラビッツ / TMR-Hiro ADV System）

用法：
  python scripts/memscan_jp.py <pid> [--min 6] [--dump out.txt] [--addr 0x...]

判据：CP932 双字节区间（0x81-0x9F / 0xE0-0xEF 起）连续 >= --min 字节，解出的串含假名。
输出：命中总数 / 最长若干条（带地址）/ 可选整段落盘。
"""
import ctypes
import ctypes.wintypes as wt
import re
import sys

k32 = ctypes.WinDLL("kernel32", use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
READABLE = {0x02, 0x04, 0x08, 0x20, 0x40, 0x80}   # R / RW / WC / ER / ERW / EWC


class MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p),
                ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wt.DWORD),
                ("RegionSize", ctypes.c_size_t),
                ("State", wt.DWORD),
                ("Protect", wt.DWORD),
                ("Type", wt.DWORD)]


JP = re.compile(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]){3,}')
KANA = re.compile(r"[ぁ-んァ-ヴ]")


def regions(h):
    addr = 0
    mbi = MBI()
    while k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        base = mbi.BaseAddress or 0
        size = mbi.RegionSize
        if mbi.State == MEM_COMMIT and (mbi.Protect & 0xFF) in READABLE:
            yield base, size, mbi.Protect
        addr = base + size
        if addr <= base:
            break


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    pid = int(sys.argv[1])
    minlen = 6
    dump = None
    only = None
    for i, a in enumerate(sys.argv):
        if a == "--min":
            minlen = int(sys.argv[i + 1])
        elif a == "--dump":
            dump = sys.argv[i + 1]
        elif a == "--addr":
            only = int(sys.argv[i + 1], 16)

    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        print(f"[E] OpenProcess 失败 err={ctypes.get_last_error()}（可能需要同位数/管理员）")
        return
    buf = ctypes.create_string_buffer(0x100000)
    read = ctypes.c_size_t(0)
    hits = []
    nreg = 0
    total = 0
    for base, size, prot in regions(h):
        if only is not None and not (base <= only < base + size):
            continue
        nreg += 1
        off = 0
        while off < size:
            chunk = min(len(buf), size - off)
            if not k32.ReadProcessMemory(h, ctypes.c_void_p(base + off), buf,
                                         ctypes.c_size_t(chunk), ctypes.byref(read)):
                off += chunk
                continue
            data = buf.raw[:read.value]
            for m in JP.finditer(data):
                try:
                    t = m.group().decode("cp932")
                except UnicodeDecodeError:
                    continue
                if len(m.group()) >= minlen and KANA.search(t):
                    hits.append((base + off + m.start(), m.group(), t))
                    total += len(t)
            off += chunk
    print(f"[i] pid={pid} 可读区 {nreg}  命中 {len(hits)} 段  日文字符 {total}")
    hits.sort(key=lambda x: -len(x[2]))
    for a, raw, t in hits[:15]:
        print(f"  {a:#010x} len={len(t):5d} {t[:70]}")
    if dump and hits:
        hits.sort(key=lambda x: x[0])
        with open(dump, "w", encoding="utf-8") as f:
            for a, raw, t in hits:
                f.write(f"{a:#010x}\t{t}\n")
        print(f"[i] 已落盘 {dump}（{len(hits)} 行）")


if __name__ == "__main__":
    main()
