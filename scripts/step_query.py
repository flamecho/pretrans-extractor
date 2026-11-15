from pathlib import Path
import json,sys,collections,re,struct
work=Path(__file__).resolve().parent.parent / '_work_step'
elts=json.loads((work/'elements.json').read_text(encoding='utf-8'))
mode=sys.argv[1]
if mode=='overview':
    summary=json.loads((work/'inspection.json').read_text(encoding='utf-8'))
    for s in summary['scenes']:
        titles=[e for e in elts if e['scene']==s['scene'] and e.get('op')==[1,4,0,0]]
        print(s['scene'],'TEXT',s['text_count'],'SEL',s['select_count'],'TITLE',[bytes.fromhex(e['params'][0]).decode('cp932') for e in titles])
    ns=collections.Counter()
    for s in summary['scenes']:ns.update(s['names'])
    print('NAMES',ns)
    macro=collections.Counter()
    for e in elts:
        if 'text' in e:macro.update(re.findall('[＊％][Ａ-Ｚ]+',e['text']))
    print('MACROS',macro)
elif mode=='scene':
    sn=int(sys.argv[2]);lo=int(sys.argv[3],0) if len(sys.argv)>3 else 0;hi=int(sys.argv[4],0) if len(sys.argv)>4 else 999999
    subset=[e for e in elts if e['scene']==sn and lo<=e['offset']<hi and e['kind'] not in ('meta','entry','comma')]
    for e in subset[:80]:
        d={k:v for k,v in e.items() if k not in ('scene','hex','end')}
        if e['kind']!='text': d['hex']=e['hex'][:200]
        if 'text' in d:d['text']=d['text'][:180]
        print(json.dumps(d,ensure_ascii=False))
    print('TOTAL',len(subset))
elif mode=='refs':
    refs=[]
    for e in elts:
        if e.get('op',[0,0])[:2]==[0,1] and e.get('op',[0,0,0])[2] in (11,12,13,14,15):
            values=[struct.unpack('<i',bytes.fromhex(x)[2:6])[0] for x in e.get('params',[]) if x.startswith('24ff') and len(x)==12]
            refs.append({'scene':e['scene'],'offset':e['offset'],'op':e['op'],'values':values,'hex':e['hex']})
    (work/'scene_refs.json').write_text(json.dumps(refs,ensure_ascii=False,indent=2),encoding='utf-8')
    counts=collections.Counter(v for r in refs for v in r['values'])
    print('TARGET COUNTS',counts)
    for r in refs:
        if any(v in (998,999,9000,1000,2000,3000,4000,5000) for v in r['values']) or r['scene'] in (100,998,999,9000): print(r)
