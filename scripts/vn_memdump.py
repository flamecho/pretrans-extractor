import ctypes, ctypes.wintypes as wt, sys, os, struct, zlib, re
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

PID = int(sys.argv[1])
OUT = os.path.join(VNTRANS_HOME, "_work_omega/dump3")
os.makedirs(OUT, exist_ok=True)
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]

class MBI64(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_ulonglong), ("AllocationBase", ctypes.c_ulonglong),
                ("AllocationProtect", wt.DWORD), ("__a1", wt.DWORD), ("RegionSize", ctypes.c_ulonglong),
                ("State", wt.DWORD), ("Protect", wt.DWORD), ("Type", wt.DWORD), ("__a2", wt.DWORD)]
MEM_COMMIT = 0x1000; PAGE_GUARD = 0x100; PAGE_NOACCESS = 0x01
PROCESS_QUERY_INFORMATION = 0x0400; PROCESS_VM_READ = 0x0010

h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, PID)
if not h:
    print("OpenProcess failed", ctypes.get_last_error()); sys.exit(1)
print("opened", PID)

idx = open(os.path.join(OUT, "index.txt"), "w")
mf = open(os.path.join(OUT, "mem.bin"), "wb")
buf = ctypes.create_string_buffer(1 << 20)
addr = 0; total = 0; regions = 0
while addr < 0x80000000:
    mbi = MBI64()
    if not k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        break
    base = mbi.BaseAddress; size = mbi.RegionSize
    if mbi.State == MEM_COMMIT and not (mbi.Protect & (PAGE_GUARD | PAGE_NOACCESS)) and size:
        off = 0; start = mf.tell(); wrote = 0; b0 = base; gap = False
        while off < size:
            n = min(1 << 20, size - off)
            got = ctypes.c_size_t(0)
            if k32.ReadProcessMemory(h, ctypes.c_void_p(base + off), buf, n, ctypes.byref(got)) and got.value:
                if gap or wrote == 0:
                    if wrote:
                        idx.write("%016x %x %x\n" % (b0, wrote, start))
                    b0 = base + off; start = mf.tell(); wrote = 0; gap = False
                mf.write(buf.raw[:got.value]); wrote += got.value; total += got.value; off += got.value
            else:
                if wrote:
                    idx.write("%016x %x %x\n" % (b0, wrote, start)); wrote = 0
                gap = True; off += n
        if wrote:
            idx.write("%016x %x %x\n" % (b0, wrote, start))
        regions += 1
    nxt = base + (size if size else 0x1000)
    addr = nxt if nxt > addr else addr + 0x1000
idx.close(); mf.close()
print("regions", regions, "bytes", total)
k32.CloseHandle(h)
