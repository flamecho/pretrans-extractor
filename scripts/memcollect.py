#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""运行中进程的日文文本高频采样器（PC 游戯 运行时提取）

背景：クレイジー★ラビッツ(TMR-Hiro) `srp.pac` 剧本是自有压缩，静态解不开；游戯把**当前场景**
解成 CP932 明文放进内存缓冲 ⇒ 每推进一个场景采一次，累积成全文。

两段式（关键：全内存扫描要 24s，跳读根本跟不上）：
  ① 冷启动／定期刷新：全量扫一遍，挑出「日文命中多」的区域作为**候选文本缓冲**；
  ② 热循环：只重读这些候选区（几百 KB），默认每 0.3s 一次 ⇒ 跳读也能逐场景收到。

用法：
  python scripts/memcollect.py <pid> <out.txt> [--interval 0.3] [--seconds 900] [--refresh 30] [--min 6]

输出：按内存地址顺序追加新出现的句子（全局去重），每次采样写 `# snapshot 时间 新增N`。
判据：CP932 双字节区连续串、含假名、长度>=min、**日文字符占比>=50%**（滤掉代码误判）、
      排除整排字库串（あぃいぅ…）。
"""
import ctypes
import ctypes.wintypes as wt
import re
import sys
import time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
READABLE = {0x02, 0x04, 0x08, 0x20, 0x40, 0x80}


class MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wt.DWORD), ("RegionSize", ctypes.c_size_t),
                ("State", wt.DWORD), ("Protect", wt.DWORD), ("Type", wt.DWORD)]


RUN = re.compile(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]|[\x20-\x7e])+')
KANA = re.compile(r"[ぁ-んァ-ヴ]")
JPCH = re.compile(r"[ぁ-んァ-ヴ一-龥０-９]")
KAJOU = re.compile(r"[ぁ-ん]{20,}|[ァ-ヴ]{20,}")


def regions(h):
    addr = 0
    mbi = MBI()
    while k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        base = mbi.BaseAddress or 0
        size = mbi.RegionSize
        if mbi.State == MEM_COMMIT and (mbi.Protect & 0xFF) in READABLE:
            yield base, size
        addr = base + size
        if addr <= base:
            break


def extract(data, base, minlen):
    out = []
    for m in RUN.finditer(data):
        b = m.group()
        if len(b) < minlen:
            continue
        try:
            t = b.decode("cp932")
        except UnicodeDecodeError:
            continue
        if not KANA.search(t) or KAJOU.search(t):
            continue
        if len(JPCH.findall(t)) / max(1, len(t)) < 0.5:
            continue
        out.append((base + m.start(), t))
    return out


def read_region(h, base, size, buf, rd):
    got = bytearray()
    off = 0
    while off < size:
        chunk = min(len(buf), size - off)
        if not k32.ReadProcessMemory(h, ctypes.c_void_p(base + off), buf,
                                     ctypes.c_size_t(chunk), ctypes.byref(rd)):
            break
        got += buf.raw[:rd.value]
        off += chunk
    return bytes(got)


def main():
    pid, outp = int(sys.argv[1]), sys.argv[2]
    interval, seconds, refresh, minlen = 0.3, 0.0, 30.0, 6
    for i, a in enumerate(sys.argv):
        if a == "--interval":
            interval = float(sys.argv[i + 1])
        elif a == "--seconds":
            seconds = float(sys.argv[i + 1])
        elif a == "--refresh":
            refresh = float(sys.argv[i + 1])
        elif a == "--min":
            minlen = int(sys.argv[i + 1])

    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        print(f"[E] OpenProcess err={ctypes.get_last_error()}")
        return
    buf = ctypes.create_string_buffer(0x100000)
    rd = ctypes.c_size_t(0)
    seen = set()
    cand = []
    last_refresh = 0.0
    t0 = time.time()
    snaps = 0
    with open(outp, "a", encoding="utf-8", newline="\n") as f:
        while True:
            now = time.time()
            if now - last_refresh >= refresh or not cand:
                cand = []
                for base, size in regions(h):
                    data = read_region(h, base, size, buf, rd)
                    hits = extract(data, base, minlen)
                    if hits:
                        cand.append((base, size, len(hits)))
                cand.sort(key=lambda x: -x[2])
                cand = cand[:12]
                last_refresh = now
                print(f"[{time.strftime('%H:%M:%S')}] 刷新候选区 {len(cand)} 个 "
                      f"({sum(c[1] for c in cand) / 1e6:.1f} MB)", flush=True)
            snap = []
            for base, size, _ in cand:
                snap += extract(read_region(h, base, size, buf, rd), base, minlen)
            snap.sort(key=lambda x: x[0])
            new = [(a, t) for a, t in snap if t not in seen]
            if new:
                seen.update(t for _, t in new)
                f.write(f"# snapshot {time.strftime('%H:%M:%S')} 新增{len(new)}\n")
                for a, t in new:
                    f.write(t.replace("\r", "") + "\n")
                f.flush()
                print(f"[{time.strftime('%H:%M:%S')}] 新增 {len(new):4d}  累计 {len(seen)}", flush=True)
            snaps += 1
            if seconds and time.time() - t0 >= seconds:
                break
            time.sleep(interval)
    print(f"[i] 结束：采样 {snaps} 次，累计 {len(seen)} 行 → {outp}")


if __name__ == "__main__":
    main()
