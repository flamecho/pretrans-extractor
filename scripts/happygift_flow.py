from pathlib import Path
import sys,json,collections,struct,argparse
W=Path(__file__).resolve().parent.parent/'_work_happygift'
ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,default=W);ap.add_argument('--start',type=int,default=9900);ap.add_argument('--dynamic-map',type=Path);args=ap.parse_args();W=args.work
dynamic_map=json.loads(args.dynamic_map.read_text('utf-8')) if args.dynamic_map else {}
sys.path.insert(0,str(W.parent/'tools'))
from rl_decomp import read_toc
from rl_parse import Parser
E=json.loads((W/'elements.json').read_text('utf-8'));by=collections.defaultdict(list)
for e in E:by[e['scene']].append(e)
I=json.loads((W/'inspection.json').read_text('utf-8'))
blob=(Path(I['source'])/'SEEN.TXT').read_bytes();toc=read_toc(blob)
entries={};nodes={};edge={};bad=[];calls=[];missing_entries=[]
for sn,rows in by.items():
 o,n=toc[sn];s=blob[o:o+n];ko,kn=struct.unpack_from('<II',s,8);kidoku=struct.unpack_from('<'+'I'*kn,s,ko)
 ep={}
 for e in rows:
  if e['kind']=='entry':
   ix=int.from_bytes(bytes.fromhex(e['hex'])[1:3],'little');v=kidoku[ix]
   if v>=1000000:ep[v-1000000]=e['offset']
 entries[sn]=ep
 for e in rows:nodes[(sn,e['offset'])]=e
def const(h):
 b=bytes.fromhex(h)
 return struct.unpack_from('<i',b,2)[0] if len(b)==6 and b[:2]==b'$\xff' else None
for sn,rows in by.items():
 for e in rows:
  a=e['offset']; nxt=(sn,e['end']); out=[nxt] if nxt in nodes else []
  k=e['kind'];op=e.get('op',[]);b=bytes.fromhex(e['hex'])
  if k=='text' and e['text'].startswith('ＳｅｅｎＥｎｄ'):out=[]
  if op[:3] in ([1,4,1201],[1,4,1202]):
   # Sys_MenuReturn::AdvanceInstructionPointer is false; this command jumps
   # to #SEEN_MENU and never falls through into the developer tail.
   import re
   config=(Path(I['source'])/'GAMEEXE.INI').read_bytes().decode('cp932')
   menu=re.search(r'^#SEEN_MENU\s*=\s*(\d+)',config,re.M)
   assert menu,(sn,a,'missing SEEN_MENU')
   target=int(menu[1]);assert target in entries and 0 in entries[target]
   out=[(target,entries[target][0])]
   edge[(sn,a)]=out
   continue
  if k=='goto':
   t=(sn,struct.unpack_from('<I',b,len(b)-4)[0]);out=[t]+(out if op[2]==5 else [])
  elif k in ('gotoif','gosub'):
   t=(sn,struct.unpack_from('<I',b,len(b)-4)[0]);out.append(t)
  elif k in ('gotoon','gotocase'):
   p=Parser(b);pos=8;pLen=p.next_expression(pos);pos+=pLen;assert b[pos]==0x7b;pos+=1
   targets=[]
   for _ in range(int.from_bytes(b[5:7],'little')):
    if k=='gotocase':
     assert b[pos]==0x28
     pos+=2 if b[pos+1]==0x29 else 2+p.next_expression(pos+1)
    targets.append((sn,struct.unpack_from('<I',b,pos)[0]));pos+=4
   assert b[pos]==0x7d
   out=targets+(out if op[2] in (8,9) else [])
  elif op[:2]==[0,1]:
   if op[2] in (10,13,17,19):out=[]
   elif op[2] in (11,12,18):
    ps=e.get('params',[]);target=const(ps[0]) if ps else None;ep=const(ps[1]) if len(ps)>1 else 0
    if target is None:
     alternatives=dynamic_map.get(f'{sn}:{a}');assert alternatives,(sn,a,target,ep)
     assert all(t in entries and ep in entries[t] for t in alternatives),(sn,a,alternatives,ep)
     out=(out if op[2]!=11 else [])+[(t,entries[t][ep]) for t in alternatives]
     calls.append({'scene':sn,'offset':a,'targets':alternatives,'entry':ep,'dynamic':True})
     edge[(sn,a)]=out
     continue
    assert target in entries,(sn,a,target,ep)
    if ep not in entries[target]:
     assert all(x['kind']!='text' or x['text'].startswith('ＳｅｅｎＥｎｄ') for x in by[target])
     missing_entries.append({'scene':sn,'offset':a,'target':target,'entry':ep})
     calls.append({'scene':sn,'offset':a,'target':target,'entry':ep})
     edge[(sn,a)]=out+[ (target,x) for x in entries[target].values()]
     continue
    t=(target,entries[target][ep]);calls.append({'scene':sn,'offset':a,'target':target,'entry':ep})
    out=(out if op[2]!=11 else [])+[t]
  for t in out:
   if t not in nodes:bad.append([sn,a,t])
  edge[(sn,a)]=out
assert not bad,bad[:8]
seen=set();todo=[(args.start,entries[args.start][0])]
while todo:
 key=todo.pop()
 if key in seen:continue
 seen.add(key);todo.extend(edge[key])
scope={sn:[] for sn in by}
for sn,a in seen:scope[sn].append(a)
for v in scope.values():v.sort()
excluded_options=[];excluded_text=[]
for e in E:
 if (e['scene'],e['offset']) in seen:continue
 if e['kind']=='select':excluded_options.append(e)
 if e['kind']=='text' and not e['text'].startswith('ＳｅｅｎＥｎｄ'):excluded_text.append(e)
result={'entrypoints':entries,'calls':calls,'reachable':scope,'excluded_options':excluded_options,'excluded_text':excluded_text,'nontext_missing_entry_calls':missing_entries}
(W/'flow.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
print('REACHABLE_SCENES',[s for s,x in scope.items() if x]);print('EXCLUDED_OPTIONS',[(e['scene'],hex(e['offset']),e['options']) for e in excluded_options]);print('EXCLUDED_TEXT',len(excluded_text),[(e['scene'],hex(e['offset']),e['text']) for e in excluded_text[:15]])
print('ENTRIES',[(s,ep) for s,ep in entries.items() if len(ep)>1][:20])
