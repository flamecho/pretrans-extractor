"""Remove only validation registry keys and restore the user's game window."""
from pathlib import Path
import argparse,json,winreg,ctypes as c
from ctypes import wintypes as w
ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,required=True)
ap.add_argument('--variant',choices=('ea','fe'),required=True);args=ap.parse_args()
prefix='OCELOT\\WHITE_'+('E' if args.variant=='ea' else 'F')+'_TRANS_CASE'
removed=[]
for case in (1,2):
    setup=json.loads((args.work/f'native_case{case}_setup.json').read_text('utf-8'))
    key=setup['registry'].removeprefix('HKCU/')
    assert key=='Software/'+prefix+str(case)
    key=key.replace('Software/','Software\\',1)
    winreg.DeleteKey(winreg.HKEY_CURRENT_USER,key);removed.append(key)
u=c.WinDLL('user32');u.SetForegroundWindow.argtypes=[w.HWND]
info=json.loads((args.work/'discovery.json').read_text('utf-8'))
restored=bool(u.SetForegroundWindow(info['windows'][0]['hwnd']))
result={'removed_test_registry_keys':removed,'user_window_restored':restored}
(args.work/'native_cleanup.json').write_text(json.dumps(result,indent=2),'utf-8')
print(json.dumps(result,indent=2))
