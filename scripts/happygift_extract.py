from pathlib import Path
import json,re,collections,hashlib,sys,argparse,subprocess
R=Path(__file__).resolve().parent.parent;W=R/'_work_happygift'
ap=argparse.ArgumentParser(description='Happy Gift: strict bytecode, reachability, default names and per-page layout.')
ap.add_argument('--source',type=Path,default=Path(r'C:\AMEDEO\DRFD'))
ap.add_argument('--work',type=Path,default=W)
ap.add_argument('--title',default='[PC-JP]誰にでも裏がある Happy Gift')
ap.add_argument('--start',type=int,default=9900)
ap.add_argument('--prepare',action='store_true',help='Rebuild bytecode and scope from SEEN.TXT')
ap.add_argument('--publish',action='store_true',help='Write the final UTF-8 BOM text')
args=ap.parse_args()
W=args.work;W.mkdir(exist_ok=True)
if args.prepare:
 for script,extra in [('happygift_inspect.py',['--source',str(args.source),'--work',str(W)]),('happygift_flow.py',['--work',str(W),'--start',str(args.start)])]:
  subprocess.run([sys.executable,'-B','-X','utf8',str(R/'tools'/script),*extra],check=True)
TITLE=args.title
E=json.loads((W/'elements.json').read_text('utf-8'))
F=json.loads((W/'flow.json').read_text('utf-8'))
I=json.loads((W/'inspection.json').read_text('utf-8'))
C=(Path(I['source'])/'GAMEEXE.INI').read_bytes().decode('cp932')
N={m[1]:m[2] for m in re.finditer(r'^#NAME\.([A-Z]+)="([^"]*)"',C,re.M)}
assert N=={'A':'桜井','B':'菜々子','C':'百恵'}
assert re.search(r'^#WINDOW\.000\.R_COMMAND_MOD=0\s*$',C,re.M)
assert re.search(r'^#WINDOW\.000\.NAME_MOD=1\s*$',C,re.M)
by=collections.defaultdict(list)
for e in E:by[e['scene']].append(e)
scope={int(sn):set(rows) for sn,rows in F['reachable'].items()}
story=sorted(sn for sn,rows in by.items() if any(e['kind']=='text' and not e['text'].startswith('ＳｅｅｎＥｎｄ') and e['offset'] in scope[sn] for e in rows))
lines=[];origins=[];pages=[];stats=collections.Counter();scene_stats=[];pending=[];name_no_quote=[];name_pages=[]
def clean(t):
 def fill(m):
  assert m[1]=='＊';key=''.join(chr(ord(c)-ord('Ａ')+ord('A')) for c in m[2]);assert key in N
  stats['macro_'+key]+=1
  return N[key]
 return re.sub(r'([＊％])([Ａ-Ｚ]+)',fill,t)
def render(t,sn,at):
 names=list(re.finditer(r'【([^】]*)】',t))
 if not names:return t,''
 assert len(names)==1 and names[0].start()==0,(sn,at,t)
 m=names[0];name=m[1];body=t[m.end():]
 stats['name_markup_chars']+=len(m[0]);stats['speaker_chars']+=len(name);stats['speaker_pages']+=1
 if not body.startswith(('「','『')):name_no_quote.append({'scene':sn,'offset':at,'name':name,'text':body})
 return name+body,name
for sn in story:
 current=[];offsets=[];segments=[];st=collections.Counter();start=len(lines);last=None
 def segment(at):
  if current:
   raw=''.join(current);current.clear();segments.append((raw,list(offsets),at));offsets.clear()
 def page(reason,at):
  segment(at)
  if not segments:return
  emitted=[];rendered=[]
  for raw,src,end in segments:
   t,speaker=render(raw,sn,at)
   if not t.strip():st['empty_layout_segments']+=1;continue
   lines.append(t);emitted.append(len(lines));rendered.append(t)
   origins.append({'line':len(lines),'scene':sn,'offsets':src,'end':end,'reason':reason,'speaker':speaker,'type':'segment'})
   st['segments']+=1
  if len(emitted)>1:
   merged=''.join(rendered);lines.append(merged)
   origins.append({'line':len(lines),'scene':sn,'offsets':[a for _,s,_ in segments for a in s],'end':at,'reason':reason,'type':'merged'})
   pages.append({'segments':emitted,'merged':len(lines),'source':f'SEEN{sn:04d}@0x{segments[0][1][0]:X}..0x{at:X}'})
   st['merged_pages']+=1
  if emitted:st['pages']+=1;st['page_end_'+reason]+=1
  segments.clear()
 for e in by[sn]:
  at=e['offset'];k=e['kind']
  if at not in scope[sn]:continue
  if k=='text':
   if e['text'].startswith('ＳｅｅｎＥｎｄ'):page('halt',at);continue
   t=clean(e['text']);current.append(t);offsets.append(at);st['records']+=1;st['source_chars']+=len(e['text']);st['expanded_chars']+=len(t)
  elif k=='func' and e['op'][:2]==[0,3]:
   op=e['op'][2]
   if op in (17,151,152,161,162,210):page('op'+str(op),at)
   elif op in (3,201):st['soft_breaks']+=1
   elif op==205:segment(at);st['same_page_pauses']+=1
   elif op in (102,206,207):raise AssertionError(('unsupported narrative message operation',sn,at,op))
  elif k=='select':
   page('select',at)
   for idx,t in enumerate(e['options']):
    t=clean(t);assert '###PRINT' not in t
    if t.strip():
     lines.append(t);origins.append({'line':len(lines),'scene':sn,'offsets':[at],'end':e['end'],'reason':'option','index':idx,'type':'option'});st['options']+=1;st['option_chars']+=len(t)
  elif k in ('goto','gotoif','gotoon','gotocase','gosub') and (current or segments):
   pending.append({'scene':sn,'offset':at,'kind':k,'current':current.copy(),'segments':segments.copy()})
  last=e
 page('eof',last['end'])
 scene_stats.append({'scene':sn,'lines':len(lines)-start,**dict(st)})
assert len(lines)==len(origins)
assert not any(re.search(r'[＊％][Ａ-Ｚ]|###PRINT|[\uf8f0-\uf8ff\ufffd]',t) for t in lines)
dest=(R/'提取结果'/f'{TITLE}.txt') if args.publish else W/'candidate.txt'
dest.parent.mkdir(exist_ok=True)
dest.write_text('\n'.join(lines)+'\n',encoding='utf-8-sig',newline='\n')
totals=collections.Counter()
for s in scene_stats:totals.update({k:v for k,v in s.items() if k not in ('scene','lines')})
result={'title':TITLE,'scope':story,'lines':len(lines),'chars':sum(map(len,lines)),'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'stats':dict(stats),'totals':dict(totals),'scenes':scene_stats,'pending':pending,'name_without_quotes':name_no_quote}
(W/'extraction.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
(W/'line_origins.json').write_text(json.dumps(origins,ensure_ascii=False),'utf-8')
(W/'layout_map.json').write_text(json.dumps({'pages':pages},ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ('scope','scenes','pending','name_without_quotes')},ensure_ascii=False,indent=2))
print('SCOPE',len(story),'PENDING',len(pending),'UNQUOTED_NAME',len(name_no_quote));print('PENDING SAMPLE',pending[:3]);print('UNQUOTED',name_no_quote[:6])
