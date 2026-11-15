"""Verify source conservation, page layout and character provenance for White EA."""
from pathlib import Path
import json,re,collections,struct,hashlib,argparse
ROOT=Path(__file__).resolve().parent.parent
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--work',type=Path,default=ROOT/'_work_polwhite_ea')
ap.add_argument('--auto-map',type=Path)
ap.add_argument('--probe',action='store_true',help='Record layout candidates before native verification')
args=ap.parse_args();W=args.work
expected_auto=({'_work_polwhite_ea':{(2000,168960),(2000,505776)},'_work_polwhite_fe':{(1100,46002),(1000,304286)}}.get(W.name,set()))
if args.auto_map:expected_auto={(x['scene'],x['offset']) for x in json.loads(args.auto_map.read_text('utf-8'))}
E=json.loads((W/'elements.json').read_text('utf-8'))
F=json.loads((W/'flow.json').read_text('utf-8'))
reachable={int(sn):set(rows) for sn,rows in F['reachable'].items()}
X=json.loads((W/'extraction.json').read_text('utf-8'))
O=json.loads((W/'line_origins.json').read_text('utf-8'))
L=Path(X['output']).read_text('utf-8-sig').splitlines()
index={(e['scene'],e['offset']):e for e in E}
used=[];ascii_rows=[];charset={};structure=[]
cjk=lambda c: 0x3040<=ord(c)<=0x30ff or 0x3400<=ord(c)<=0x4dbf or 0x4e00<=ord(c)<=0x9fff or 0x3000<=ord(c)<=0x303f or 0xff01<=ord(c)<=0xff60 or 0xffe0<=ord(c)<=0xffee
for o,t in zip(O,L):
    es=[index[(o['scene'],at)] for at in o['offsets']]
    expected=re.sub(r'【[^】]*】','',''.join(e['text'] for e in es))
    assert t==expected,(o,t,expected)
    if o['type']=='segment':used.extend((o['scene'],at) for at in o['offsets'])
    if any(0<ord(c)<128 for c in t):ascii_rows.append({**o,'text':t})
    for c in t:
        if not cjk(c):
            item=charset.setdefault(c,{'char':c,'codepoint':f'U+{ord(c):04X}','count':0,'lines':[],'samples':[]})
            item['count']+=1
            if o['line'] not in item['lines']:item['lines'].append(o['line'])
            if len(item['samples'])<3 and not any(s['line']==o['line'] for s in item['samples']):item['samples'].append({**o,'text':t})
    pairs=[('「','」'),('『','』'),('（','）')]
    mismatch=[(a,b,t.count(a),t.count(b)) for a,b in pairs if t.count(a)!=t.count(b)]
    multi=[(a,b,t.count(a),t.count(b)) for a,b in pairs if t.count(a)>1 or t.count(b)>1]
    if mismatch or multi:structure.append({**o,'text':t,'mismatch':mismatch,'multiple':multi})
expected={(e['scene'],e['offset']) for e in E if e['scene'] in X['scope'] and e['kind']=='text' and e['offset'] in reachable[e['scene']] and not e['text'].startswith('ＳｅｅｎＥｎｄ')}
assert len(used)==len(set(used)) and set(used)==expected
assert len(L)==len(O)==X['lines']
source=(ROOT/'scripts/rlvm-source/string_utilities.cc').read_text('utf-8')
section=source.split('bool IsKinsoku(int codepoint)')[1].split('0x0};')[0]
kinsoku={int(h,16) for h in re.findall(r'0x([0-9a-f]+)',section)}
roman=lambda c: 'A'<=c<='Z' or 'a'<=c<='z' or c in "'-"
def const(h):
    b=bytes.fromhex(h);assert len(b)==6 and b[:2]==b'$\xff'
    return struct.unpack_from('<i',b,2)[0]
windows={n:{'x':0,'row':0,'indent':0,'name':False,'start':None,'limit':limit,'height':height} for n,limit,height in [(0,30*22,5),(1,18*22,15)]}
active=0;overflow=[];rendered_pages=0;max_rows=collections.Counter();pages_by_window=collections.Counter();hanging=[]
def clear(n):
    global rendered_pages
    v=windows[n]
    if v['start'] is not None:rendered_pages+=1;pages_by_window[n]+=1
    v.update(x=0,row=0,indent=0,name=False,start=None)
for e in [r for sn in X['scope'] for r in E if r['scene']==sn]:
    if e['scene'] not in X['scope'] or e['offset'] not in reachable[e['scene']]:continue
    v=windows[active];at=e['offset']
    if e['kind']=='text' and not e['text'].startswith('ＳｅｅｎＥｎｄ'):
        if v['start'] is None:v['start']=at
        # Parse the same name tokens used by TextoutLongOperation; NAME_MOD=2
        # only updates indentation state and does not emit the token text.
        text=e['text'];p=0
        while p<len(text):
            if text[p]=='【':
                end=text.index('】',p);p=end+1;v['name']=True;continue
            c=text[p];rest=text[p+1:];width=11 if ord(c)<127 else 22
            is_k=ord(c) in kinsoku or c==' '
            br=False
            if not(is_k and v['x']+width<=v['limit']+23):
                if v['x']+width>v['limit']:br=True
                elif not is_k:
                    final=v['x']+width
                    for n in rest:
                        if ord(n) in kinsoku:
                            final+=11 if ord(n)<127 else 22
                            if final>v['limit']+23:br=True;break
                        elif roman(n):
                            final+=11
                            if final>v['limit']:br=True;break
                        else:break
            if br:v['row']+=1;v['x']=v['indent']
            if v['row']>=v['height']:
                overflow.append({'scene':e['scene'],'start':v['start'],'offset':at,'index':p,'window':active,'row':v['row'],'text':text})
                clear(active);v['start']=at
            v['x']+=width
            if v['name'] and c in '「『（':v['indent']=v['x']
            v['name']=False
            max_rows[active]=max(max_rows[active],v['row'])
            if v['x']>v['limit']:hanging.append({'scene':e['scene'],'offset':at,'char':c,'window':active,'x':v['x']})
            p+=1
    elif e.get('op',[])[:2]==[0,3]:
        op=e['op'][2]
        if op==102:active=const(e['params'][0])
        elif op in (3,201):
            if op==3:v['indent']=0
            v['x']=v['indent'];v['row']+=1
        elif op in (151,152,210):clear(active)
        elif op in (17,161,162):
            for n in windows:clear(n)
for n in windows:clear(n)
summary={'source_records':len(used),'source_equality':True,'output_sha256':hashlib.sha256(Path(X['output']).read_bytes()).hexdigest(),
         'ascii_lines':len(ascii_rows),'charset_count':len(charset),'structure_candidates':len(structure),
         'mismatch_segments':sum(bool(s['mismatch']) and s['type']=='segment' for s in structure),
         'mismatch_merged':sum(bool(s['mismatch']) and s['type']=='merged' for s in structure),
         'rendered_pages':rendered_pages,'pages_by_window':dict(pages_by_window),'max_rows':dict(max_rows),
         'automatic_pages':overflow,'unexpected_overflows':[s for s in overflow if (s['scene'],s['offset']) not in expected_auto],'hanging_count':len(hanging)}
for name,obj in [('audit',summary),('ascii_audit',ascii_rows),('charset_sources',list(charset.values())),('structure_audit',structure),('layout_audit',{'summary':summary,'hanging':hanging})]:
    (W/(name+'.json')).write_text(json.dumps(obj,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
print('CHARSET',[(x['char'],x['count'],x['samples'][0]['text']) for x in charset.values()])
print('STRUCTURE SAMPLES',[(s['line'],s['type'],s['text'],s['mismatch']) for s in structure if s['mismatch']][:10])
if not args.probe:
    assert {(s['scene'],s['offset']) for s in overflow}==expected_auto,overflow
    assert {(p['scene'],p['end']) for p in json.loads((W/'page_details.json').read_text('utf-8')) if p['reason']=='auto'}==expected_auto
    assert rendered_pages==X['stats']['pages'],(rendered_pages,X['stats']['pages'])
