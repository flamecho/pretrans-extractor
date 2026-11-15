"""Polifonica Memories White EA: checked RealLive bytecode, click/page export.

Both story windows use NAME_MOD=2: TextWindow::SetName consumes the name
without displaying it. spause 205 keeps the current page; pause 17 clears all
windows because R_COMMAND_MOD=0. par/br are layout breaks only. Window 102
only changes the active window and is not itself a page delimiter.
"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
from pathlib import Path as _ScriptPath
_SCRIPT_DIR = _ScriptPath(__file__).resolve().parent
from pathlib import Path
import argparse, subprocess, sys, json, collections, re, struct, hashlib
ROOT=Path(os.environ.get('VNTRANS_HOME', os.getcwd()))
TITLE='[PC-JP]神曲奏界ポリフォニカ Memories White～エンドレスアリア～'
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--variant',choices=('ea','fe'),default='ea')
ap.add_argument('--source',type=Path)
ap.add_argument('--work',type=Path)
ap.add_argument('--auto-map',type=Path,help='Native-verified record-start page boundaries')
ap.add_argument('--prepare',action='store_true')
ap.add_argument('--publish',action='store_true')
args=ap.parse_args()
if args.variant=='fe':TITLE='[PC-JP]神曲奏界ポリフォニカ Memories White～ファーストエモーション～'
args.source=args.source or Path('C:/OCELOT/WHITE_'+('E' if args.variant=='ea' else 'F'))
W=args.work or ROOT/('_work_polwhite_'+args.variant);W.mkdir(exist_ok=True)
if args.prepare:
    for script,extra in [('happygift_inspect.py',['--source',str(args.source),'--work',str(W)]),
                         ('_lib/happygift_flow.py',['--work',str(W),'--start',str(200 if args.variant=='ea' else 100)])]:
        subprocess.run([sys.executable,'-B','-X','utf8',str(_SCRIPT_DIR/script),*extra],check=True)
E=json.loads((W/'elements.json').read_text('utf-8'))
I=json.loads((W/'inspection.json').read_text('utf-8'))
F=json.loads((W/'flow.json').read_text('utf-8'))
assert I['seen_sha256']=={'ea':'4d43fbd6edaf92b4fe68bc547662b352f5b516114b05777b099debd442cbe3e0','fe':'f15d63a0025972f6d33d0e1945b1278ddd4011cd962dd09286ae665bbdeac000'}[args.variant],'Unsupported source revision'
# Native 1.4.7.3 tests confirm two window-1 capacity resets at record starts.
# case1 steps05/06: before "彼女は、険しい顔をしていた。"
# case2 steps04/05: before "お嬢さま！？". Both are between click segments;
# hidden name markup in the latter is consumed before the first visible glyph.
automatic_page_starts=({(2000,168960),(2000,505776)} if args.variant=='ea' else {(1100,46002),(1000,304286)})
if args.auto_map:
    automatic_page_starts={(x['scene'],x['offset']) for x in json.loads(args.auto_map.read_text('utf-8'))}
config=args.source.joinpath('GAMEEXE.INI').read_bytes().decode('cp932').replace('\r','')
for window in (0,1):
    assert re.search(fr'^#WINDOW\.{window:03d}\.NAME_MOD=2$',config,re.M)
    assert re.search(fr'^#WINDOW\.{window:03d}\.R_COMMAND_MOD=0$',config,re.M)
scope={int(sn):set(rows) for sn,rows in F['reachable'].items()}
story=sorted({e['scene'] for e in E if e['kind']=='text' and e['offset'] in scope[e['scene']] and not e['text'].startswith('ＳｅｅｎＥｎｄ')})
assert story==([2000] if args.variant=='ea' else [1000,1100]),story
if args.variant=='fe':story=[1100,1000]
lines=[];origins=[];pages=[];page_details=[];stats=collections.Counter();used=[];pending=[]
def const(h):
    b=bytes.fromhex(h)
    assert len(b)==6 and b[:2]==b'$\xff',h
    return struct.unpack_from('<i',b,2)[0]
def display(raw):
    assert not re.search(r'[＊％][Ａ-Ｚ]|###PRINT',raw),raw
    for match in re.finditer(r'【([^】]*)】',raw):
        stats['hidden_names']+=1;stats['hidden_markup_chars']+=len(match[0])
    text=re.sub(r'【[^】]*】','',raw)
    assert '【' not in text and '】' not in text,raw
    return text
for sn in story:
    current=[];offsets=[];segments=[];active_window=0;page_window=None
    def segment(at):
        if current:
            raw=''.join(current);current.clear()
            segments.append({'raw':raw,'offsets':offsets.copy(),'end':at,'window':page_window})
            offsets.clear()
    def page(reason,at):
        segment(at)
        if not segments:return
        emitted=[];texts=[];source_offsets=[]
        for s in segments:
            text=display(s['raw'])
            assert text and text.strip(),s
            lines.append(text);emitted.append(len(lines));texts.append(text)
            source_offsets.extend(s['offsets']);used.extend((sn,a) for a in s['offsets'])
            origins.append({'line':len(lines),'scene':sn,'offsets':s['offsets'],'end':s['end'],
                            'reason':reason,'window':s['window'],'type':'segment'})
        merged=None
        if len(emitted)>1:
            lines.append(''.join(texts));merged=len(lines)
            origins.append({'line':merged,'scene':sn,'offsets':source_offsets,'end':at,
                            'reason':reason,'window':segments[0]['window'],'type':'merged'})
            pages.append({'segments':emitted,'merged':merged,'source':f'SEEN{sn:04d}@0x{source_offsets[0]:X}..0x{at:X}'})
        page_details.append({'scene':sn,'start':source_offsets[0],'end':at,'reason':reason,
                             'window':segments[0]['window'],'segments':emitted,'merged':merged})
        stats['pages']+=1;stats['segments']+=len(emitted);stats['merged_pages']+=merged is not None
        stats['page_end_'+reason]+=1;segments.clear()
    rows=[e for e in E if e['scene']==sn]
    for e in rows:
        at=e['offset'];k=e['kind']
        if at not in scope[sn]:continue
        if k=='text':
            if e['text'].startswith('ＳｅｅｎＥｎｄ'):
                page('halt',at);continue
            if (sn,at) in automatic_page_starts:
                assert active_window in (0,1) and segments and not current,(sn,at)
                page('auto',at)
            if not current and not segments:page_window=active_window
            assert active_window==page_window,(sn,at,active_window,page_window)
            current.append(e['text']);offsets.append(at);stats['records']+=1;stats['source_chars']+=len(e['text'])
        elif e.get('op',[])[:2]==[0,3]:
            op=e['op'][2]
            if op in (17,151,152,161,162,210):page('op'+str(op),at)
            elif op==205:
                segment(at);stats['same_page_pauses']+=1
            elif op in (3,201):stats['soft_breaks']+=1
            elif op==102:
                assert not current and not segments,(sn,at,'window switch with text')
                active_window=const(e['params'][0]);assert active_window in (0,1)
                stats['window_switches']+=1
            elif op==120:stats['ruby_'+str(e['op'][3])]+=1
            else:raise AssertionError(('unsupported message operation',sn,at,e['op']))
        elif k=='select':raise AssertionError(('unexpected selection',sn,at))
        elif (k in ('goto','gotoif','gotoon','gotocase','gosub') or e.get('op',[])[:2]==[0,1]) and (current or segments):
            if args.variant=='fe' and e.get('op',[])[:3]==[0,1,12] and const(e['params'][0])==9:
                assert all(r.get('op',[])[:2]!=[0,3] and (r['kind']!='text' or r['text'].startswith('ＳｅｅｎＥｎｄ')) for r in E if r['scene']==9)
                stats['nontext_calls_with_page']+=1
            else:pending.append({'scene':sn,'offset':at,'op':e.get('op'),'current':current.copy(),'segments':segments.copy()})
    page('eof',rows[-1]['end'])
assert not pending,pending[:3]
expected={(e['scene'],e['offset']) for e in E if e['scene'] in story and e['kind']=='text' and e['offset'] in scope[e['scene']] and not e['text'].startswith('ＳｅｅｎＥｎｄ')}
assert len(used)==len(set(used)) and set(used)==expected
assert stats['source_chars']-stats['hidden_markup_chars']==sum(len(t) for t,o in zip(lines,origins) if o['type']=='segment')
assert not any(re.search(r'[\uf8f0-\uf8ff\ufffd]|###PRINT|[＊％][Ａ-Ｚ]',t) for t in lines)
dest=ROOT/'提取结果'/(TITLE+'.txt') if args.publish else W/'candidate.txt'
dest.parent.mkdir(exist_ok=True)
dest.write_text('\n'.join(lines)+'\n',encoding='utf-8-sig',newline='\n')
result={'title':TITLE,'scope':story,'lines':len(lines),'chars':sum(map(len,lines)),
        'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),
        'stats':dict(stats),'pending':pending,'output':str(dest)}
for name,obj in [('extraction',result),('line_origins',origins),('layout_map',{'pages':pages}),('page_details',page_details)]:
    (W/(name+'.json')).write_text(json.dumps(obj,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
print('FIRST LINES',lines[:12])
