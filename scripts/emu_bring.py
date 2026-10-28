# -*- coding: utf-8 -*-
"""把模拟器（PCSX2/PPSSPP）窗口置前并截图。标题匹配在脚本内完成，免 CJK 参数传递。"""
import ctypes, ctypes.wintypes as wt, sys, time
from PIL import ImageGrab
u32 = ctypes.windll.user32
u32.SetProcessDPIAware()
KEYS = ("pcsx2", "meine", "\u30de\u30a4\u30cd\u30ea\u30fc\u30d9", "ppsspp", "cus tom", "custom drive", "\u30ab\u30b9\u30bf\u30e0")
def wins():
    out=[]
    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def cb(h, l):
        if u32.IsWindowVisible(h):
            n=u32.GetWindowTextLengthW(h)
            if n:
                b=ctypes.create_unicode_buffer(n+1); u32.GetWindowTextW(h,b,n+1)
                out.append((h,b.value))
        return True
    u32.EnumWindows(cb,0); return out
def bring(h):
    HWND_TOPMOST=-1; SWP=(2|1|0x40)
    u32.ShowWindow(h,3)
    u32.SetWindowPos(h,HWND_TOPMOST,0,0,0,0,SWP)
    u32.BringWindowToTop(h); u32.SetForegroundWindow(h)
    time.sleep(1.2)
def main():
    shot=sys.argv[1] if len(sys.argv)>1 else None
    ws=wins()
    for h,t in ws: print(hex(h), t[:60])
    tgt=None
    for h,t in ws:
        tl=t.lower()
        if any(k in tl for k in KEYS): tgt=h; break
    print("target:", hex(tgt) if tgt else None)
    if tgt: bring(tgt)
    if shot:
        ImageGrab.grab(all_screens=True).save(shot); print("shot", shot)
if __name__=='__main__': main()
