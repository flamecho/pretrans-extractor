"""Build isolated native-engine excerpts to check two automatic-page candidates.

Original installation, disc, scripts and saved data remain read-only. This test
uses an executable copy, a separate registry/save location, and original
scenario bytes with only an initial jump added before the excerpt.
"""
from pathlib import Path
import sys,json,re,shutil,struct,winreg,argparse,subprocess
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'tools'))
from rl_decomp import read_toc,scenario,XOR
from kare_dx_extract import decompress_audit
ap=argparse.ArgumentParser();ap.add_argument('--case',type=int,choices=(1,2),required=True)
ap.add_argument('--variant',choices=('ea','fe'),default='ea');args=ap.parse_args()
W=ROOT/('_work_polwhite_'+args.variant)
target=({1:168278,2:505041} if args.variant=='ea' else {1:45333,2:303991})[args.case]
scene=2000 if args.variant=='ea' else {1:1100,2:1000}[args.case]
window=1 if args.variant=='ea' else {1:1,2:0}[args.case]
out=W/f'native_case{args.case}';out.mkdir(exist_ok=True)
source=Path('C:/OCELOT/WHITE_'+('E' if args.variant=='ea' else 'F'))
exe=(source/'REALLIVE.EXE').read_bytes()
original_class=b'VisualArts_System2000_RealLive'
test_class=f'VisualArts_System2000_TestLiv{args.case}'.encode('ascii')
assert len(original_class)==len(test_class) and exe.count(original_class)==1
# Isolate only the window class used by the native single-instance check.
# Rendering and message-processing machine code are left byte-for-byte intact.
(out/'REALLIVE.EXE').write_bytes(exe.replace(original_class,test_class))
original_key='OCELOT\\WHITE_'+('E' if args.variant=='ea' else 'F')
keyname=f'{original_key}_TRANS_CASE{args.case}'
config=(source/'GAMEEXE.INI').read_bytes().decode('cp932').replace('\r','')
config=re.sub(r'^#SEEN_START=.*$', '#SEEN_START='+str(scene),config,flags=re.M)
config=re.sub(r'^#REGNAME.*$', '#REGNAME = "'+keyname.replace('\\','\\\\')+'"',config,flags=re.M)
config=re.sub(r'^#INIT_MESSAGE_SPEED=.*$', '#INIT_MESSAGE_SPEED=0',config,flags=re.M)
config=re.sub(r'^#INIT_SCREENMODE=.*$', '#INIT_SCREENMODE=1',config,flags=re.M)
config=re.sub(r'^#SAVE_USE=.*$', '#SAVE_USE=0',config,flags=re.M)
config=re.sub(r'^#INIT_KOEMODE=.*$', '#INIT_KOEMODE=1',config,flags=re.M)
config=re.sub(r'^#SUBTITLE=.*$', '#SUBTITLE=0',config,flags=re.M)
config=re.sub(r'^#CAPTION=.*$', f'#CAPTION="White{args.variant.upper()} native validation {args.case}"',config,flags=re.M)
(out/'GAMEEXE.INI').write_bytes(config.replace('\n','\r\n').encode('cp932'))
with winreg.OpenKey(winreg.HKEY_CURRENT_USER,'Software\\'+original_key) as src, winreg.CreateKey(winreg.HKEY_CURRENT_USER,'Software\\'+keyname) as dst:
    i=0
    while True:
        try:name,value,kind=winreg.EnumValue(src,i)
        except OSError:break
        if name=='SAV_FOLDER':value=str(out)
        if name=='DAT_FOLDER':value=str(out)
        if name=='DAT_EXIST':value='1' if isinstance(value,str) else struct.pack('<I',1) if isinstance(value,bytes) else 1
        winreg.SetValueEx(dst,name,0,kind,value);i+=1
blob=(source/'SEEN.TXT').read_bytes();toc=read_toc(blob)
offset,length=toc[scene];hl,ver,co,dl,cl,s=scenario(blob,offset,length)
code,used=decompress_audit(s[co:co+cl],dl);code=bytearray(code)
entries=json.loads((W/'flow.json').read_text('utf-8'))['entrypoints']
initial=entries[str(scene)]['0'];patch_at=initial+3
assert code[initial:patch_at]==b'!\0\0'
prefix=b'\x23\x00\x03\x66\x00\x01\x00\x00(\x24\xff'+struct.pack('<i',window)+b')'+b'\x23\x00\x01\x00\x00\x00\x00\x00'+struct.pack('<I',target)
code[patch_at:patch_at+len(prefix)]=prefix
literal=bytearray()
for p in range(0,len(code),8):literal.append(255);literal.extend(code[p:p+8])
plain=struct.pack('<II',len(literal)+8,len(code))+literal
encoded=bytes(b^XOR[i&255] for i,b in enumerate(plain))
assert decompress_audit(encoded,len(code))[0]==code
head=bytearray(s[:co]);struct.pack_into('<II',head,0x24,len(code),len(encoded))
entry=head+encoded;table=bytearray(80000);struct.pack_into('<II',table,scene*8,80000,len(entry))
(out/'SEEN.TXT').write_bytes(table+entry)
for name in ('g00','dat','bgm','koe'):
    link=out/name
    if not link.exists():
        ps_path=str(link).replace("'","''")
        ps_target=str(Path('D:/')/name).replace("'","''")
        subprocess.run(['powershell','-NoProfile','-Command',f"New-Item -ItemType Junction -Path '{ps_path}' -Target '{ps_target}' | Out-Null"],check=True)
(W/f'native_case{args.case}_setup.json').write_text(json.dumps({'case':args.case,'scene':scene,'window':window,'target':target,'path':str(out),'registry':'HKCU/Software/'+keyname,'native_exe':str(out/'REALLIVE.EXE'),'patch_range':[patch_at,patch_at+len(prefix)]},indent=2),'utf-8')
print(out)
