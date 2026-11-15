from pathlib import Path
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import json,re,collections,unicodedata,sys,struct
R=Path(VNTRANS_HOME);W=R/'_work_dareura';sys.path.insert(0,str(R/'tools'))
E=json.loads((W/'elements.json').read_text('utf-8'));F=json.loads((W/'flow.json').read_text('utf-8'));X=json.loads((W/'extraction.json').read_text('utf-8'))
O=json.loads((W/'line_origins.json').read_text('utf-8'));dest=R/'提取结果'/f"{X['title']}.txt";L=(dest if dest.exists() else W/'candidate.txt').read_text('utf-8-sig').splitlines()
index={(e['scene'],e['offset']):e for e in E};names={'Ａ':'桜井','Ｂ':'菜々子','Ｃ':'百恵'}
def expand(s):return re.sub(r'＊([Ａ-Ｃ])',lambda m:names[m[1]],s)
used=[];ascii_rows=[];char_sources={};long=[]
for o,t in zip(O,L):
 es=[index[(o['scene'],a)] for a in o['offsets']]
 if o['type']=='segment':
  raw=expand(''.join(e['text'] for e in es))
  expected=re.sub(r'^【([^】]*)】',lambda m:m[1],raw)
  used.extend((o['scene'],a) for a in o['offsets'])
 else:
  assert o['type']=='option';expected=expand(es[0]['options'][o['index']])
 assert expected==t,(o,t,expected)
 if any(0<ord(c)<128 for c in t):ascii_rows.append({'line':o['line'],'scene':o['scene'],'offsets':o['offsets'],'text':t})
 for c in t:
  n=ord(c)
  if not (0x3040<=n<=0x30ff or 0x3400<=n<=0x4dbf or 0x4e00<=n<=0x9fff or 0x3000<=n<=0x303f or 0xff01<=n<=0xff60 or 0xffe0<=n<=0xffee):
   a=char_sources.setdefault(c,{'char':c,'codepoint':f'U+{n:04X}','count':0,'samples':[]});a['count']+=1
   if len(a['samples'])<3:a['samples'].append({'line':o['line'],'scene':o['scene'],'offsets':o['offsets'],'text':t})
 body=t[len(o.get('speaker','')):] if o['type']=='segment' else t
 width=sum(1 if unicodedata.east_asian_width(c) in 'WFA' else .5 for c in body)
 if o['type']=='segment' and width>69:long.append({'line':o['line'],'scene':o['scene'],'width':width,'text':body})
expected={(e['scene'],e['offset']) for e in E if e['scene'] in X['scope'] and e['kind']=='text' and e['offset'] in F['reachable'][str(e['scene'])] and not e['text'].startswith('ＳｅｅｎＥｎｄ')}
assert len(used)==len(set(used)) and set(used)==expected
assert len(L)==len(O)==X['lines']
runtime=[o['line'] for o,t in zip(O,L) if t=='百恵「起きなさい。いつまで寝てるつもり？」']
assert runtime
font_ops=[e for e in E if e['scene'] in X['scope'] and e.get('op',[])[:3]==[0,3,101]]
font_values=collections.Counter(tuple(e.get('params',[])) for e in font_ops if e['op'][3]==0)
result={'source_records':len(used),'source_equality':True,'ascii_lines':len(ascii_rows),'charset_count':len(char_sources),'long_width_candidates':long,'font_sizes':[(p,n) for p,n in font_values.items()],'runtime_lines':runtime}
(W/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
(W/'ascii_audit.json').write_text(json.dumps(ascii_rows,ensure_ascii=False,indent=2),'utf-8')
(W/'charset_sources.json').write_text(json.dumps(list(char_sources.values()),ensure_ascii=False,indent=2),'utf-8')
print('AUDIT',json.dumps(result,ensure_ascii=False))
print('ASCII',[(x['line'],x['text']) for x in ascii_rows])
