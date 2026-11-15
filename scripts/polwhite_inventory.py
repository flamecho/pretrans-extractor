"""Inventory archive, disc and installation; verify relevant files only."""
from pathlib import Path
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import subprocess, json, hashlib, collections, argparse
ROOT=Path(__file__).resolve().parent.parent
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--work',type=Path,default=ROOT/'_work_polwhite_ea')
ap.add_argument('--source',type=Path,default=Path('C:/OCELOT/WHITE_E'))
ap.add_argument('--title',default='[PC-JP]神曲奏界ポリフォニカ Memories White～エンドレスアリア～')
ap.add_argument('--archive',type=Path)
ap.add_argument('--disc',type=Path,default=Path('D:/'))
args=ap.parse_args();WORK=args.work;WORK.mkdir(exist_ok=True);SOURCE=args.source;TITLE=args.title
archive=args.archive or Path(os.path.join(VNTRANS_HOME, '还没做'))/(TITLE+'.rar')
iso=next((archive.parent/TITLE).rglob('*.ISO'));DISC=args.disc
seven=Path('C:/Program Files/7-Zip/7z.exe')
def listing(path, tag):
    p=subprocess.run([str(seven),'l','-slt','-sccUTF-8','-potoame',str(path)],capture_output=True,check=True)
    text=p.stdout.decode('utf-8').replace('\r\n','\n')
    (WORK/(tag+'_manifest.txt')).write_text(text,'utf-8')
    entries=[]
    for block in text.split('----------\n',1)[1].strip().split('\n\n'):
        entry={}
        for line in block.splitlines():
            if ' = ' in line:
                key,value=line.split(' = ',1);entry[key]=value
        if entry:entries.append(entry)
    (WORK/(tag+'_manifest.json')).write_text(json.dumps(entries,ensure_ascii=False,indent=2),'utf-8')
    return entries
rar_entries=listing(archive,'rar')
iso_entries=listing(iso,'iso')
disc=[]
for p in DISC.rglob('*'):
    if p.is_file():disc.append({'path':p.relative_to(DISC).as_posix(),'size':p.stat().st_size,'extension':p.suffix.lower()})
(WORK/'disc_manifest.json').write_text(json.dumps(disc,ensure_ascii=False,indent=2),'utf-8')
installed=[{'path':p.relative_to(SOURCE).as_posix(),'size':p.stat().st_size} for p in SOURCE.rglob('*') if p.is_file() and 'SAVEDATA' not in p.parts]
verified={}
for name in ('SEEN.TXT','GAMEEXE.INI','REALLIVE.EXE'):
    a=next(p for p in DISC.iterdir() if p.name.upper()==name)
    b=SOURCE/name
    ha=hashlib.sha256(a.read_bytes()).hexdigest();hb=hashlib.sha256(b.read_bytes()).hexdigest()
    verified[name]={'disc_sha256':ha,'installed_sha256':hb,'equal':ha==hb}
    assert ha==hb,(name,ha,hb)
small={}
for item in disc:
    p=DISC/item['path']
    if p.name.upper()!='SEEN.TXT' and p.suffix.lower() in ('.ini','.inf','.env','.html','.txt'):
        data=p.read_bytes()
        try:
            small[item['path']]=data.decode('cp932')
        except UnicodeDecodeError:
            small[item['path']]='BINARY: '+data.hex()
        (WORK/('disc_'+p.name+'.txt')).write_text(small[item['path']],'utf-8')
headers=[]
for item in disc:
    p=DISC/item['path']
    if p.suffix.lower() in ('.dat','.gan','.hik','.ard','.cgm','.pac','.pak'):
        with p.open('rb') as f:head=f.read(64)
        headers.append({'path':item['path'],'size':item['size'],'header':head.hex()})
(WORK/'resource_headers.json').write_text(json.dumps(headers,ensure_ascii=False,indent=2),'utf-8')
summary={'archive':str(archive),'archive_size':archive.stat().st_size,'rar_entries':len(rar_entries),
         'iso':str(iso),'iso_size':iso.stat().st_size,'iso_entries':len(iso_entries),'disc_files':len(disc),
         'disc_extensions':dict(collections.Counter(e['extension'] for e in disc)),
         'installed':installed,'verified':verified,'small_files':list(small),
         'unknown_headers':headers[:12]}
(WORK/'inventory.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({k:v for k,v in summary.items() if k not in ('installed','small_files','unknown_headers')},ensure_ascii=False,indent=2))
