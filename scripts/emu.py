#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""模拟器辅助：截屏 + 发键（Windows，PIL + ctypes，无第三方 GUI 依赖）。

用法：
  python scripts/emu.py shot out.png                 # 全屏截图
  python scripts/emu.py win                          # 列出可见顶层窗口标题
  python scripts/emu.py focus "<标题片段>"            # 置前
  python scripts/emu.py key <vk> [次数] [间隔ms]      # 发单键（vk 如 13=Return, 32=Space, 120=F9）
  python scripts/emu.py seq "13x20,32x3"            # 依次发键序列
"""
import ctypes, ctypes.wintypes as wt, sys, time
from PIL import ImageGrab

u32 = ctypes.windll.user32
u32.SetProcessDPIAware()


def shot(path):
    im = ImageGrab.grab(all_screens=True)
    im.save(path)
    print('saved', path, im.size)


def enum_windows():
    out = []
    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def cb(hwnd, lp):
        if u32.IsWindowVisible(hwnd):
            n = u32.GetWindowTextLengthW(hwnd)
            if n:
                b = ctypes.create_unicode_buffer(n + 1)
                u32.GetWindowTextW(hwnd, b, n + 1)
                out.append((hwnd, b.value))
        return True
    u32.EnumWindows(cb, 0)
    return out


def focus_exe(exe):
    pid_by = {}
    for hwnd, title in enum_windows():
        pid = wt.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        try:
            import subprocess
            name = subprocess.run(['tasklist','/FI','PID eq %d'%pid.value,'/NH'],
                                  capture_output=True, text=True).stdout.lower()
        except Exception:
            name = ''
        if exe.lower() in name:
            u32.ShowWindow(hwnd, 9); u32.SetForegroundWindow(hwnd)
            time.sleep(0.5); print('focus', hex(hwnd), title); return hwnd
    print('exe not found:', exe); return None


def focus(sub):
    for hwnd, title in enum_windows():
        if sub.lower() in title.lower():
            u32.ShowWindow(hwnd, 9)          # SW_RESTORE
            u32.SetForegroundWindow(hwnd)
            time.sleep(0.4)
            print('focus', hex(hwnd), title)
            return hwnd
    print('not found:', sub)
    return None


KEYUP, KEYDOWN = 2, 0


def key(vk, n=1, delay=0.35, hold=0.05):
    for _ in range(n):
        u32.keybd_event(vk, 0, KEYDOWN, 0)
        time.sleep(hold)
        u32.keybd_event(vk, 0, KEYUP, 0)
        time.sleep(delay)


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a:
        print(__doc__); sys.exit(1)
    if a[0] == 'shot':
        shot(a[1])
    elif a[0] == 'win':
        for h, t in enum_windows():
            print(hex(h), t[:70])
    elif a[0] == 'focus':
        focus(a[1])
    elif a[0] == 'front':
        h = int(a[1], 16)
        HWND_TOPMOST, SWP_NOMOVE, SWP_NOSIZE, SWP_SHOWWINDOW = -1, 2, 1, 0x40
        u32.SetWindowPos(h, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
        u32.ShowWindow(h, 3)  # SW_MAXIMIZE
        u32.BringWindowToTop(h)
        u32.SetForegroundWindow(h)
        time.sleep(1.0)
        print('front', a[1])
    elif a[0] == 'fh':
        h = int(a[1], 16)
        u32.ShowWindow(h, 9); u32.SetForegroundWindow(h); time.sleep(0.5); print('focus hwnd', a[1])
    elif a[0] == 'focusexe':
        focus_exe(a[1])
    elif a[0] == 'key':
        vk = int(a[1]); n = int(a[2]) if len(a) > 2 else 1
        d = (float(a[3]) / 1000.0) if len(a) > 3 else 0.35
        key(vk, n, d)
    elif a[0] == 'seq':
        for part in a[1].split(','):
            v, _, n = part.partition('x')
            key(int(v), int(n or 1))
    else:
        print(__doc__)
