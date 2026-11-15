"""Locate the running Polifonica installation and capture its window without input."""
from pathlib import Path
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import ctypes as c
from ctypes import wintypes as w
import json
import argparse

ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--work', type=Path, default=ROOT / '_work_polwhite_ea')
ap.add_argument('--title-filter', default='ポリフォニカ')
args = ap.parse_args()
WORK = args.work
WORK.mkdir(exist_ok=True)
k = c.WinDLL('kernel32', use_last_error=True)
u = c.WinDLL('user32', use_last_error=True)
u.SetProcessDPIAware()
k.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
k.OpenProcess.restype = w.HANDLE
k.QueryFullProcessImageNameW.argtypes = [w.HANDLE, w.DWORD, w.LPWSTR, c.POINTER(w.DWORD)]
k.CloseHandle.argtypes = [w.HANDLE]
info = []
CALLBACK = c.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
@CALLBACK
def visit(hwnd, param):
    title = c.create_unicode_buffer(1024)
    u.GetWindowTextW(hwnd, title, len(title))
    if args.title_filter not in title.value:
        return True
    pid = w.DWORD()
    u.GetWindowThreadProcessId(hwnd, c.byref(pid))
    handle = k.OpenProcess(0x1000, False, pid.value)
    path = c.create_unicode_buffer(32768)
    size = w.DWORD(len(path))
    ok = bool(handle and k.QueryFullProcessImageNameW(handle, 0, path, c.byref(size)))
    error = c.get_last_error()
    if handle:
        k.CloseHandle(handle)
    rect = w.RECT()
    u.GetWindowRect(hwnd, c.byref(rect))
    item = {'pid': pid.value, 'hwnd': hwnd, 'title': title.value,
            'path': path.value if ok else None, 'error': error,
            'rect': [rect.left, rect.top, rect.right, rect.bottom]}
    try:
        from PIL import Image
        g = c.WinDLL('gdi32', use_last_error=True)
        u.GetWindowDC.argtypes = [w.HWND]
        u.GetWindowDC.restype = w.HDC
        u.ReleaseDC.argtypes = [w.HWND, w.HDC]
        u.PrintWindow.argtypes = [w.HWND, w.HDC, w.UINT]
        g.CreateCompatibleDC.argtypes = [w.HDC]
        g.CreateCompatibleDC.restype = w.HDC
        g.CreateCompatibleBitmap.argtypes = [w.HDC, c.c_int, c.c_int]
        g.CreateCompatibleBitmap.restype = w.HBITMAP
        g.SelectObject.argtypes = [w.HDC, w.HANDLE]
        g.SelectObject.restype = w.HANDLE
        g.GetBitmapBits.argtypes = [w.HBITMAP, w.LONG, c.c_void_p]
        g.DeleteObject.argtypes = [w.HANDLE]
        g.DeleteDC.argtypes = [w.HDC]
        width, height = rect.right-rect.left, rect.bottom-rect.top
        dc = u.GetWindowDC(hwnd)
        memory = g.CreateCompatibleDC(dc)
        bitmap = g.CreateCompatibleBitmap(dc, width, height)
        old = g.SelectObject(memory, bitmap)
        item['print_window'] = bool(u.PrintWindow(hwnd, memory, 2))
        data = c.create_string_buffer(width*height*4)
        assert g.GetBitmapBits(bitmap, len(data), data) == len(data)
        Image.frombuffer('RGB', (width, height), data.raw, 'raw', 'BGRX', 0, -1).save(WORK/'runtime.png')
        g.SelectObject(memory, old)
        g.DeleteObject(bitmap)
        g.DeleteDC(memory)
        u.ReleaseDC(hwnd, dc)
        if not item['print_window']:
            import time
            from PIL import ImageGrab
            item['foreground_set'] = bool(u.SetForegroundWindow(hwnd))
            time.sleep(0.4)
            ImageGrab.grab(bbox=tuple(item['rect']), all_screens=True).save(WORK/'runtime.png')
        item['capture'] = str(WORK/'runtime.png')
    except Exception as ex:
        item['capture_error'] = repr(ex)
    info.append(item)
    return True
u.EnumWindows(visit, 0)
archives = [str(p) for p in Path(VNTRANS_HOME).rglob('*Memories White*')]
result = {'windows': info, 'archives': archives}
(WORK/'discovery.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), 'utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
