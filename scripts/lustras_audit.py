"""Independent source, resource and output audit for Innocentria Lustras."""
from pathlib import Path
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
from collections import Counter
import argparse, ctypes as c, hashlib, importlib.util, json, math, re, struct
from ctypes import wintypes as w

BASE = Path(__file__).resolve().parents[1]
ROOT = Path(os.path.join(VNTRANS_HOME, '还没做/[PC-JP]ラストラス/[PC-JP]ラストラス'))
EVIDENCE = BASE/'解析报告/证据/[PC-JP]ラストラス'
WORK = BASE/'_work_lustras'
PYTHON = Path('<本地路径>')

def save(name, obj):
    (EVIDENCE/name).write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def run():
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    dat=(ROOT/'nscript.dat').read_bytes()
    script=bytes(v^0x84 for v in dat).decode('cp932',errors='strict')
    lines=script.splitlines()
    summary=json.loads((EVIDENCE/'summary.json').read_text(encoding='utf-8'))
    coverage=json.loads((EVIDENCE/'coverage.json').read_text(encoding='utf-8'))
    src=json.loads((EVIDENCE/'source_map.json').read_text(encoding='utf-8'))
    pages=json.loads((EVIDENCE/'pages.json').read_text(encoding='utf-8'))
    output=BASE/'提取结果/[PC-JP]ラストラス.txt'
    ob=output.read_bytes(); rows=ob.decode('utf-8-sig',errors='strict').splitlines()
    assert hashlib.sha256(dat).hexdigest()==summary['source_sha256']
    assert hashlib.sha256(ob).hexdigest()==summary['output_sha256']
    assert len(rows)==summary['rows']==len(src)
    assert ob.startswith(b'\xef\xbb\xbf') and b'\r' not in ob
    assert all(row.strip() for row in rows)
    assert all(x['output']==i+1 for i,x in enumerate(src))
    candidates={n for n,s in enumerate(lines,1) if s.strip() and not s.lstrip().startswith((';','*',':','~','"')) and not re.match(r'[A-Za-z_]',s.lstrip())}
    consumed=set(coverage['consumed']); excluded={v['line'] for v in coverage['excluded']}
    unaccounted=candidates-consumed-excluded
    assert not unaccounted, sorted(unaccounted)
    label=''; label_text=Counter(); active=Counter(); headings=[]
    for n,s in enumerate(lines,1):
        t=s.strip()
        if t.startswith('*'): label=t.split(';')[0].split()[0][1:]
        if n in consumed:label_text[label]+=1
        if t and not t.startswith(';') and re.match(r'[A-Za-z_]',t):active[t.split()[0]]+=1
        if t.startswith(';') and ('■' in t or '＜' in t) and len(headings)<100:headings.append({'line':n,'text':t})
    mapped_lines={n for item in src for n in item['source']}
    names={n for p in pages for d in p['display'] if d.get('name') for n in [d['line']]}
    empty_consumed=[]
    for n in sorted(consumed-mapped_lines-names):
        t=re.sub(r'#[A-Fa-f0-9]{6}','',lines[n-1]).replace('\\','').replace('@','').strip()
        if t: raise AssertionError(('unmapped nonempty source',n,t))
        empty_consumed.append(n)
    capacity=[]; width_excess=[]
    for p in pages:
        count=0; detail=[]
        for d in p['display']:
            t=d['text']
            # NScripter's fixed-cell windows: CP932 single-byte half-cell,
            # double-byte full-cell. Ruby has already been reduced to its base.
            width=sum(1 if len(ch.encode('cp932'))==2 else .5 for ch in t)
            wrap=max(1,math.ceil(width/p['window'][0]))
            count+=wrap
            if width>p['window'][0]:
                item={'page':p['page'],'line':d['line'],'columns':width,'window':p['window'],'text':t}
                width_excess.append(item);detail.append(item)
        if count>p['window'][1]:capacity.append({'page':p['page'],'rows':count,'window':p['window'],'display':p['display'],'width_excess':detail})
    ascii_rows=[dict(output=i+1,text=t,source=src[i]) for i,t in enumerate(rows) if re.search(r'[\x21-\x7e]',t)]
    duplicates=[{'first':i,'second':i+1,'text':rows[i],'source_first':src[i-1],'source_second':src[i]} for i in range(1,len(rows)) if rows[i]==rows[i-1]]
    name_nonquote=[dict(item,text=rows[item['output']-1]) for item in src if item.get('speaker') and not rows[item['output']-1][len(item['speaker']):].startswith(('「','『','（'))]
    archive_manifest=[]
    for archive in sorted(ROOT.glob('*.nsa')):
        with archive.open('rb') as f:
            count,base=struct.unpack('>HI',f.read(6));index=f.read(base-6)
        pos=0;members=[]
        for _ in range(count):
            end=index.index(0,pos);name=index[pos:end].decode('cp932',errors='strict')
            flag,off,stored,original=struct.unpack_from('>BIII',index,end+1);pos=end+14
            members.append(dict(name=name,flag=flag,offset=base+off,stored=stored,original=original))
        assert pos==base-6 and max(x['offset']+x['stored'] for x in members)==archive.stat().st_size
        assert len({x['name'].lower() for x in members})==len(members)
        archive_manifest.append(dict(archive=archive.name,bytes=archive.stat().st_size,count=count,base=base,extensions=dict(Counter(Path(x['name']).suffix.lower() for x in members)),compression=dict(Counter(x['flag'] for x in members)),members=members))
    save('nsa_manifest.json',archive_manifest)
    files=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size) for p in sorted(ROOT.rglob('*')) if p.is_file()]
    save('source_manifest.json',files)
    agm=ROOT/'がんばれ城条さん！/がんばれ城条さん！.agm'
    b=agm.read_bytes()
    runs=[m.group().decode('cp932',errors='strict') for m in re.finditer(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]|[\x20-\x7e\xa1-\xdf]){3,}',b)]
    audit=dict(source_sha256=summary['source_sha256'],output_sha256=summary['output_sha256'],exe_sha256=digest(ROOT/'ラストラス.exe'),candidate_text_lines=len(candidates),consumed=len(consumed),consumed_nontext_commands=sorted(consumed-candidates),excluded=coverage['excluded'],unaccounted=sorted(unaccounted),mapped_lines=len(mapped_lines),name_lines=len(names),empty_consumed=empty_consumed,output_kinds=dict(Counter(x['kind'] for x in src)),text_labels=dict(label_text),active_commands=dict(active),capacity_candidates=capacity,width_excess=width_excess,ascii_rows=ascii_rows,adjacent_duplicates=duplicates,named_nonquotes=name_nonquote,minigame=dict(header=b[:40].hex(),bytes=len(b),readable_runs=runs),headings=headings)
    save('final_source_audit.json',audit)
    print(json.dumps({k:audit[k] for k in ['exe_sha256','candidate_text_lines','consumed','consumed_nontext_commands','empty_consumed','output_kinds','text_labels','excluded']},ensure_ascii=False,indent=2))
    print('CAPACITY',len(capacity),json.dumps(capacity[:3],ensure_ascii=False))
    print('WIDTH EXCESS',len(width_excess),json.dumps(width_excess[:8],ensure_ascii=False))
    print('ASCII',len(ascii_rows),json.dumps(ascii_rows[:5],ensure_ascii=False))
    print('DUPLICATES',len(duplicates),json.dumps(duplicates,ensure_ascii=False))
    print('NAMED NONQUOTES',len(name_nonquote));print('MINIGAME RUNS',runs[:30])

def capture(pid,filename='runtime_current.png'):
    from PIL import Image
    user=c.WinDLL('user32',use_last_error=True);gdi=c.WinDLL('gdi32',use_last_error=True)
    user.SetProcessDPIAware()
    callback=c.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM);windows=[]
    @callback
    def enum(hwnd,lp):
        value=w.DWORD();user.GetWindowThreadProcessId(hwnd,c.byref(value))
        if value.value==pid:
            title=c.create_unicode_buffer(1024);user.GetWindowTextW(hwnd,title,1024)
            rect=w.RECT();user.GetClientRect(hwnd,c.byref(rect))
            windows.append((hwnd,title.value,rect.right,rect.bottom))
        return True
    user.EnumWindows(enum,0)
    user.GetDC.argtypes=[w.HWND];user.GetDC.restype=w.HDC
    gdi.CreateCompatibleDC.argtypes=[w.HDC];gdi.CreateCompatibleDC.restype=w.HDC
    gdi.CreateCompatibleBitmap.argtypes=[w.HDC,c.c_int,c.c_int];gdi.CreateCompatibleBitmap.restype=w.HBITMAP
    gdi.SelectObject.argtypes=[w.HDC,w.HGDIOBJ];gdi.SelectObject.restype=w.HGDIOBJ
    user.PrintWindow.argtypes=[w.HWND,w.HDC,w.UINT]
    gdi.GetDIBits.argtypes=[w.HDC,w.HBITMAP,w.UINT,w.UINT,c.c_void_p,c.c_void_p,w.UINT]
    gdi.DeleteObject.argtypes=[w.HGDIOBJ];gdi.DeleteDC.argtypes=[w.HDC];user.ReleaseDC.argtypes=[w.HWND,w.HDC]
    class INFO(c.Structure):
        _fields_=[('size',w.DWORD),('width',w.LONG),('height',w.LONG),('planes',w.WORD),('bits',w.WORD),('compression',w.DWORD),('imageSize',w.DWORD),('xppm',w.LONG),('yppm',w.LONG),('used',w.DWORD),('important',w.DWORD)]
    for hwnd,title,width,height in windows:
        if width<200 or height<150:continue
        dc=user.GetDC(hwnd);mem=gdi.CreateCompatibleDC(dc);bmp=gdi.CreateCompatibleBitmap(dc,width,height);old=gdi.SelectObject(mem,bmp)
        try:
            ok=user.PrintWindow(hwnd,mem,1);buf=c.create_string_buffer(width*height*4)
            info=INFO(c.sizeof(INFO),width,-height,1,32,0,0,0,0,0,0)
            n=gdi.GetDIBits(mem,bmp,0,height,buf,c.byref(info),0)
            if ok and n:
                target=filename if width>=600 else Path(filename).stem+'_dialog.png'
                path=EVIDENCE/target;Image.frombytes('RGB',(width,height),buf.raw,'raw','BGRX').save(path)
                print('CAPTURE',title,width,height,str(path));save(Path(filename).stem+'.json',dict(pid=pid,title=title,width=width,height=height,method='PrintWindow, read only, no input sent'))
        finally:
            gdi.SelectObject(mem,old);gdi.DeleteObject(bmp);gdi.DeleteDC(mem);user.ReleaseDC(hwnd,dc)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--capture',type=int);parser.add_argument('--filename',default='runtime_current.png');args=parser.parse_args()
    if args.capture:capture(args.capture,args.filename)
    else:run()
