"""STEP: rlvm-derived parser/decompressor; current-game GAMEEXE evidence.
pause 0:3:17 is the click boundary with WINDOW.000.R_COMMAND_MOD=0.
br 201 / par 3 are layout breaks; ruby 120 arguments are glosses.
NAME_MOD=1 draws name labels; original #NAME.A/B supply macro defaults.
No width, punctuation, quote balancing, or lexical filtering determines boundaries.
"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import argparse
from _lib.step_records import parse_records
from pathlib import Path
import json,re,collections,sys,hashlib
ROOT=Path(os.environ.get('VNTRANS_HOME', os.getcwd()))
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--source', type=Path)
ap.add_argument('--work', type=Path, default=ROOT / '_work_step')
ap.add_argument('--out', type=Path)
ap.add_argument('--publish', action='store_true')
args = ap.parse_args()
WORK = args.work
WORK.mkdir(parents=True, exist_ok=True)
SOURCE = args.source or next((WORK / 'source').rglob('SEEN.TXT')).parent
TITLE='[PC-JP]STEP -二人の関係は一歩ずつ-'
ELTS, SCENES = parse_records(SOURCE)
CONFIG=(SOURCE / 'GAMEEXE.INI').read_bytes().decode('cp932')
NAMES={m.group(1):m.group(2) for m in re.finditer(r'^#NAME\.([A-Z]+)="([^"]*)"',CONFIG,re.M)}
assert NAMES['A']=='秋野' and NAMES['B']=='みのり'
assert re.search(r'^#WINDOW\.000\.R_COMMAND_MOD=0\s*$',CONFIG,re.M)
assert re.search(r'^#WINDOW\.000\.NAME_MOD=1\s*$',CONFIG,re.M)
HIST=SCENES['histogram']
assert not any(HIST.get(f'func 0:3:{op}/{ov}',0) for op in (102,205,206,207,210) for ov in range(3))
def clean(t):
    def name(m):
        assert m.group(1)=='＊',m.group(0)
        return NAMES[''.join(chr(ord(x)-ord('Ａ')+ord('A')) for x in m.group(2))]
    return re.sub(r'([＊％])([Ａ-Ｚ]+)',name,t)

# Structural scope: all scenes containing rendered text and referenced by scene
# jump/gosub commands are included. 9000 has zero incoming references and loops
# three sample options back to its own entry (development test). System scenes
# contain only the Halt sentinel, never narrative Textout elements.
refs = [{'values': [int.from_bytes(bytes.fromhex(x)[2:6], 'little', signed=True)
                    for x in e.get('params', []) if x.startswith('24ff') and len(x) == 12]}
        for e in ELTS if e.get('op', [0, 0])[:2] == [0, 1]
        and e.get('op', [0, 0, 0])[2] in (11, 12, 13, 14, 15)]
targets={v for r in refs for v in r['values']}
body={s['scene'] for s in SCENES['scenes'] if s['text_count']>1}
assert body-targets=={9000},body-targets
story=body-{9000}
order=sorted(story-{998,999})+[999,998]
lines=[];origins=[];pages=[];stats=collections.Counter();scene_stats=[];pending=[];nonquote=[];name_locations=[]
for sn in order:
    elts=[e for e in ELTS if e['scene']==sn]
    current=[];source=[];start=len(lines);st=collections.Counter();names=collections.Counter()
    def flush(reason,at):
        if not current:return
        raw=''.join(current);current.clear()
        t=raw.rstrip();speaker=''
        marks=list(re.finditer(r'【([^】]*)】',t))
        if marks:
            name_locations.append({'scene':sn,'offsets':list(source),'marks':[(m.start(),m.group(1)) for m in marks],'text':t})
            assert len(marks)==1 and marks[0].start()==0,(sn,at,t)
            m=marks[0];speaker=m.group(1);t=t[m.end():]
            st['name_markup_chars']+=len(m.group(0));st['speaker_chars']+=len(speaker);st['speaker_pages']+=1;names[speaker]+=1
            if not t.startswith(('「','『')):
                nonquote.append({'scene':sn,'offsets':list(source),'text':t,'speaker':speaker})
            t=speaker+t
        if t.strip():
            lines.append(t);o={'line':len(lines),'scene':sn,'offsets':list(source),'end':at,'reason':reason,'speaker':speaker}
            origins.append(o);pages.append(o);st['pages']+=1;st['raw_page_chars']+=len(raw);st['trim_chars']+=len(raw)-len(raw.rstrip())
        else:
            st['empty_layout_pages']+=1;st['empty_layout_chars']+=len(raw)
        source.clear()
    for e in elts:
        k=e['kind'];a=e['offset']
        if k=='text':
            if e['text'].startswith('ＳｅｅｎＥｎｄ'):
                flush('halt',a);st['halts']+=1;continue
            current.append(clean(e['text']));source.append(a);st['text_records']+=1
            st['source_chars']+=len(e['text']);st['expanded_chars']+=len(clean(e['text']))
        elif k=='func' and e['op'][:2]==[0,3]:
            op=e['op'][2];stats[f'msg_{op}']+=1
            if op in (17,151,152,161,162,210):flush(f'op{op}',a)
            elif op in (3,201):st['soft_breaks']+=1
        elif k=='select':
            flush('select',a)
            for idx,t in enumerate(e['options']):
                t=clean(t).strip();assert '###PRINT' not in t
                if t:
                    lines.append(t);origins.append({'line':len(lines),'scene':sn,'offsets':[a],'option_index':idx,'reason':'option'})
                    st['options']+=1;st['option_chars']+=len(t)
        elif k in ('goto','gotoif','gotoon','gotocase','gosub') and current:
            pending.append({'scene':sn,'offset':a,'kind':k,'text_offsets':list(source),'hex':e['hex']})
    flush('eof',elts[-1]['end'])
    scene_stats.append({'scene':sn,'lines':len(lines)-start,'names':dict(names),**dict(st)})
assert len(origins)==len(lines)
assert not any('〔未解析〕' in t or re.search('[＊％][Ａ-Ｚ]',t) for t in lines)
dest = args.out or (ROOT / '提取结果' / f'{TITLE}.txt' if args.publish else WORK / 'candidate.txt')
dest.parent.mkdir(exist_ok=True)
dest.write_text('\n'.join(lines)+'\n',encoding='utf-8-sig',newline='\n')
totals=collections.Counter()
for st in scene_stats:
    totals.update({k:v for k,v in st.items() if isinstance(v,int) and k not in ('scene','lines')})
result={'title':TITLE,'scope':order,'excluded':[s['scene'] for s in SCENES['scenes'] if s['scene'] not in story],'lines':len(lines),'chars':sum(map(len,lines)),'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'totals':dict(totals),'stats':dict(stats),'scenes':scene_stats,'flow_pending':pending,'name_without_quote':nonquote}
(WORK/'extraction.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
(WORK/'line_origins.json').write_text(json.dumps(origins,ensure_ascii=False),encoding='utf-8')
(WORK/'name_locations.json').write_text(json.dumps(name_locations,ensure_ascii=False),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ('scenes','flow_pending','scope','excluded')},ensure_ascii=False,indent=2))
print('FLOW_PENDING',len(pending));print(json.dumps(pending[:10],ensure_ascii=False,indent=2))
