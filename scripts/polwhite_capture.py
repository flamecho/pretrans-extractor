"""Capture and advance only an isolated native validation process."""
from pathlib import Path
import ctypes as c
from ctypes import wintypes as w
import argparse,time,json
from PIL import ImageGrab
ap=argparse.ArgumentParser()
ap.add_argument('--pid',type=int,required=True)
ap.add_argument('--work',type=Path,required=True)
ap.add_argument('--variant',choices=('ea','fe'),required=True)
ap.add_argument('--case',type=int,required=True)
ap.add_argument('--steps',type=int,default=1)
ap.add_argument('--first',type=int,default=0)
ap.add_argument('--confirm-font',action='store_true')
args=ap.parse_args()
u=c.WinDLL('user32',use_last_error=True);u.SetProcessDPIAware()
u.SendMessageW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM]
u.ShowWindow.argtypes=[w.HWND,c.c_int]
u.GetWindowRect.argtypes=[w.HWND,c.POINTER(w.RECT)]
u.SetForegroundWindow.argtypes=[w.HWND]
u.GetForegroundWindow.restype=w.HWND
u.keybd_event.argtypes=[w.BYTE,w.BYTE,w.DWORD,c.c_size_t]
callback=c.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM);found=[];dialogs=[]
prefix=f'White{args.variant.upper()} native validation'
@callback
def enum(hwnd,lparam):
    pid=w.DWORD();u.GetWindowThreadProcessId(hwnd,c.byref(pid))
    if pid.value==args.pid:
        title=c.create_unicode_buffer(1024);u.GetWindowTextW(hwnd,title,1024)
        if title.value.startswith(prefix):found.append((hwnd,title.value))
        classname=c.create_unicode_buffer(128);u.GetClassNameW(hwnd,classname,128)
        if classname.value=='#32770':dialogs.append(hwnd)
    return True
u.EnumWindows(enum,0)
assert len(found)==1,found
hwnd,title=found[0];u.EnumChildWindows(hwnd,enum,0)
if args.confirm_font:
    assert len(dialogs)<=1,dialogs
    if dialogs:u.SendMessageW(dialogs[0],0x111,1,0);time.sleep(.5)
u.ShowWindow(hwnd,9);u.SetForegroundWindow(hwnd);time.sleep(.7)
log=[]
for n in range(args.first,args.first+args.steps):
    u.SetForegroundWindow(hwnd);time.sleep(.1)
    rect=w.RECT();u.GetWindowRect(hwnd,c.byref(rect))
    path=args.work/f'native_case{args.case}_step{n:02d}.png'
    ImageGrab.grab(bbox=(rect.left,rect.top,rect.right,rect.bottom),all_screens=True).save(path)
    log.append({'step':n,'capture':str(path),'window':hwnd,'title':title})
    if n!=args.first+args.steps-1:
        assert u.GetForegroundWindow()==hwnd,'Test window lost focus'
        u.keybd_event(0x0d,0,0,0);time.sleep(.06)
        u.keybd_event(0x0d,0,2,0);time.sleep(.8)
(args.work/f'native_case{args.case}_capture.json').write_text(json.dumps(log,indent=2),'utf-8')
print(json.dumps(log,indent=2))
