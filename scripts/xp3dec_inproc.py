# -*- coding: utf-8 -*-
"""XP3 逐文件加密的通用解法：在真实游戏进程内 in-process 调用注册的 filter 回调。

背景（TARHS『図書室のネヴァジスタ THE FOOL』实证）：
- XP3 内容 `plain -> 逐字节加密(L) -> 可选 zlib -> 磁盘`；`flags&1==0` 的文件内容**仍是密文**。
- filter 是 `TheFool.tpm`(= `sigdata.t01`) 里的 `xp3dec.dll`（PE32 i386，ImageBase 0x10000000），
  `V2Link`@0x100023e0 用 TVPSetXP3ArchiveExtractionFilter 注册回调 0x10001f30
  （__stdcall，1 参数 tTVPXP3ExtractionFilterInfo：SizeOfSelf=0x18 / u64 Offset / Buffer / BufferSize / FileHash=adlr）。
- 密钥 K/G 是运行期量（G 由 V2Link 对本 exe/tpm + 目录树全文件哈希累加生成，K 由 G 经 61 轮 CRC32 派生）
  ⇒ 纯静态 Unicorn 仿真必然失败；**必须在真实进程里调**。
- 铁律：**off 参数必须传 0**（传 segm 偏移全错）；解出的每件明文满足 zlib.adler32(plain) == adlr。

用法：
  python xp3dec_inproc.py <game_exe> <dll_name> <filter_rva_hex> <data.xp3> <out_dir>

例：
  python xp3dec_inproc.py "C:\\...\\TheFool.eXe" TheFool.tpm 0x1F30 "C:\\...\\data.xp3" unpack
先手动启动游戏（让它完成插件初始化），再运行本脚本；脚本会自己找进程与模块基址。
"""
import ctypes
import ctypes.wintypes as wt
import os
import struct
import sys
import time
import zlib

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
psapi = ctypes.WinDLL('psapi', use_last_error=True)

PROCESS_ALL = 0x1F0FFF
MEM_COMMIT_RESERVE = 0x3000
PAGE_READWRITE = 0x04
TH32CS_SNAPPROCESS = 0x00000002
MAX_PATH = 260


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [('dwSize', wt.DWORD), ('cntUsage', wt.DWORD),
                ('th32ProcessID', wt.DWORD),
                ('th32DefaultHeapID', ctypes.POINTER(ctypes.c_ulong)),
                ('th32ModuleID', wt.DWORD), ('cntThreads', wt.DWORD),
                ('th32ParentProcessID', wt.DWORD),
                ('pcPriClassBase', ctypes.c_long), ('dwFlags', wt.DWORD),
                ('szExeFile', wt.WCHAR * MAX_PATH)]


def find_pid(name):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == -1:
        return []
    pe = PROCESSENTRY32W()
    pe.dwSize = ctypes.sizeof(pe)
    out = []
    ok = k32.Process32FirstW(snap, ctypes.byref(pe))
    while ok:
        if pe.szExeFile.lower() == name.lower():
            out.append(pe.th32ProcessID)
        ok = k32.Process32NextW(snap, ctypes.byref(pe))
    k32.CloseHandle(snap)
    return out


def module_base(pid, want):
    h = k32.OpenProcess(0x0410, False, pid)
    if not h:
        return None
    arr = (wt.HMODULE * 1024)()
    need = wt.DWORD()
    if not psapi.EnumProcessModulesEx(h, ctypes.byref(arr), ctypes.sizeof(arr),
                                      ctypes.byref(need), 3):
        k32.CloseHandle(h)
        return None
    n = need.value // ctypes.sizeof(wt.HMODULE)
    buf = ctypes.create_unicode_buffer(MAX_PATH)
    found = None
    for i in range(n):
        psapi.GetModuleBaseNameW(h, arr[i], buf, MAX_PATH)
        if buf.value.lower() == want.lower():
            found = arr[i]
            break
    k32.CloseHandle(h)
    return found


def main():
    if len(sys.argv) < 6:
        raise SystemExit(__doc__)
    exe_name = os.path.basename(sys.argv[1])
    dll_name = sys.argv[2]
    filt_rva = int(sys.argv[3], 16)
    xp3_path = sys.argv[4]
    out_dir = sys.argv[5]
    log_path = os.path.join(os.path.dirname(out_dir.rstrip('\\/')) or '.', 'extract_log.txt')

    idx_path = os.path.splitext(xp3_path)[0] + '_index.json'
    if not os.path.exists(idx_path):
        raise SystemExit('index json missing, run xp3dec_index.py first: ' + idx_path)
    import json
    idx = json.load(open(idx_path, encoding='utf-8'))

    pids = find_pid(exe_name)
    if not pids:
        raise SystemExit('game not running; launch "%s" first' % exe_name)
    pid = pids[0]
    base = module_base(pid, dll_name)
    if not base:
        raise SystemExit('module %s not found in pid %d' % (dll_name, pid))
    print('pid', pid, 'module', dll_name, 'base', hex(base))

    h = k32.OpenProcess(PROCESS_ALL, False, pid)
    if not h:
        raise SystemExit('OpenProcess fail %d' % ctypes.get_last_error())

    k32.VirtualAllocEx.restype = ctypes.c_void_p
    k32.VirtualAllocEx.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                   wt.DWORD, wt.DWORD]

    def rpm(addr, n):
        buf = ctypes.create_string_buffer(n)
        got = ctypes.c_size_t()
        if not k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, n, ctypes.byref(got)):
            raise OSError('RPM %#x err %d' % (addr, ctypes.get_last_error()))
        return buf.raw[:got.value]

    def wpm(addr, data):
        got = ctypes.c_size_t()
        if not k32.WriteProcessMemory(h, ctypes.c_void_p(addr), data, len(data), ctypes.byref(got)):
            raise OSError('WPM %#x err %d' % (addr, ctypes.get_last_error()))
        return got.value

    cap = max(max(e['psize'] for e in idx), max(e['usize'] for e in idx)) + 0x1000
    cap = (cap + 0xFFF) & ~0xFFF
    print('entries', len(idx), 'cap', cap)

    INFO = k32.VirtualAllocEx(h, None, 0x1000, MEM_COMMIT_RESERVE, PAGE_READWRITE)
    BUF = k32.VirtualAllocEx(h, None, cap, MEM_COMMIT_RESERVE, PAGE_READWRITE)
    FILTER = base + filt_rva

    def call_filter(data, adlr):
        wpm(BUF, bytes(data))
        # tTVPXP3ExtractionFilterInfo (24 B), Offset 必须传 0
        info = (struct.pack('<I', 0x18) + struct.pack('<Q', 0) +
                struct.pack('<I', BUF) + struct.pack('<I', len(data)) +
                struct.pack('<I', adlr))
        wpm(INFO, info)
        tid = wt.DWORD()
        th = k32.CreateRemoteThread(h, None, 0, ctypes.c_void_p(FILTER),
                                    ctypes.c_void_p(INFO), 0, ctypes.byref(tid))
        if not th:
            raise OSError('CreateRemoteThread err %d' % ctypes.get_last_error())
        k32.WaitForSingleObject(th, 60000)
        code = wt.DWORD()
        k32.GetExitCodeThread(th, ctypes.byref(code))
        k32.CloseHandle(th)
        return rpm(BUF, len(data)), code.value

    xp = open(xp3_path, 'rb')
    os.makedirs(out_dir, exist_ok=True)
    log = open(log_path, 'w', encoding='utf-8')
    stat = {'ok': 0, 'adler_bad': 0, 'inflate_fail': 0, 'error': 0, 'bytes': 0}
    t0 = time.time()
    for k, e in enumerate(idx):
        name = e['name']
        seg = e['segs'][0]
        xp.seek(seg[1])
        raw = xp.read(seg[3])
        stage = raw
        if raw[:2] in (b'\x78\xda', b'\x78\x9c'):
            try:
                stage = zlib.decompress(raw)
            except Exception as ex:
                stat['inflate_fail'] += 1
                log.write('INFLATEFAIL %s %s\n' % (name, ex))
        try:
            out, code = call_filter(stage, e['adlr'])
        except Exception as ex:
            stat['error'] += 1
            log.write('ERROR %s %s\n' % (name, ex))
            continue
        if (zlib.adler32(out) & 0xFFFFFFFF) == e['adlr']:
            stat['ok'] += 1
        else:
            stat['adler_bad'] += 1
            log.write('ADLERBAD %s adlr=%08x got=%08x exit=%#x len=%d\n' %
                      (name, e['adlr'], zlib.adler32(out) & 0xFFFFFFFF, code, len(out)))
        stat['bytes'] += len(out)
        dest = os.path.join(out_dir, (name or 'unnamed').replace('/', os.sep))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'wb') as f:
            f.write(out)
        if (k + 1) % 200 == 0:
            print('%d/%d %.1fs ok=%d bad=%d err=%d' %
                  (k + 1, len(idx), time.time() - t0, stat['ok'], stat['adler_bad'], stat['error']))
            sys.stdout.flush()
    log.close()
    print('DONE %.1fs' % (time.time() - t0), stat)


if __name__ == '__main__':
    main()
