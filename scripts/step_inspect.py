from pathlib import Path
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import sys, shutil, collections, json, struct
WORK = Path(__file__).resolve().parent.parent / '_work_step'
LIB = WORK/'lib'
LIB.mkdir(exist_ok=True)
for name in ('rl_decomp.py','rl_parse.py','kare_dx_extract.py'):
    shutil.copyfile(Path(os.path.join(VNTRANS_HOME, 'tools'))/name, LIB/name)
sys.path.insert(0,str(LIB))
from rl_decomp import read_toc, scenario, decompress
from rl_parse import Parser
from kare_dx_extract import unquote, decompress_audit
game = next((WORK/'source').rglob('SEEN.TXT')).parent
blob=(game/'SEEN.TXT').read_bytes()
toc=read_toc(blob)
assert all(80000<=off and off+length<=len(blob) for off,length in toc.values())
end=80000
for sn,(off,length) in sorted(toc.items(),key=lambda kv:kv[1][0]):
    assert off==end,(sn,off,end)
    end=off+length
records=[]; scenes=[]; histogram=collections.Counter(); texts=collections.Counter(); params=collections.Counter(); msgsamples={}
(WORK/'code').mkdir(exist_ok=True)
for sn,(off,length) in sorted(toc.items()):
    h,v,co,dl,cl,s=scenario(blob,off,length)
    assert h==464 and v==10002 and co+cl==length,(sn,h,v,co,cl,length)
    code=decompress(s[co:co+cl],dl)
    check,used=decompress_audit(s[co:co+cl],dl)
    assert code==check and len(code)==dl
    (WORK/'code'/f'SEEN{sn:04d}.bin').write_bytes(code)
    p=Parser(code); elts=[]; hist=collections.Counter(); ns=collections.Counter(); sample=[]; ps=[]
    while not p.eof():
        a=p.p; kind,val=p.read_element(); assert a<p.p<=len(code),(sn,a,p.p)
        e={'scene':sn,'offset':a,'end':p.p,'kind':kind,'hex':code[a:p.p].hex()}
        key=kind
        if kind=='text':
            e['text']=unquote(val);texts[sn]+=1
            ns.update(__import__('re').findall(r'【([^】]*)】',e['text']))
            if len(sample)<4: sample.append(e['text'][:160])
        elif kind not in ('comma','meta','entry','expr'):
            mt,mo,op,ov,extra=val
            e['op']=[mt,mo,op,ov];key=f'{kind} {mt}:{mo}:{op}/{ov}'
            if 'opts' in extra: e['options']=[unquote(x) for x in extra['opts']]
            if 'params' in extra:
                e['params']=[x.hex() for x in extra['params']]
                for x in extra['params']:
                    if any(c>=0x80 for c in x):
                        params[key]+=1
                        try: t=unquote(x)
                        except UnicodeDecodeError:t=repr(x)
                        if len(ps)<8:ps.append({'offset':a,'op':e['op'],'value':t[:200]})
            if (mt,mo)==(0,3):
                k=f'{op}/{ov}'
                if k not in msgsamples:msgsamples[k]={'scene':sn,'offset':a,'hex':e['hex']}
        hist[key]+=1;histogram[key]+=1;elts.append(e)
    assert p.p==len(code)
    records.extend(elts)
    scenes.append({'scene':sn,'offset':off,'stored':length,'code_bytes':dl,'compressed':cl,'consumed':used,'trailing_hex':s[co+used:co+cl].hex(),'elements':len(elts),'text_count':hist['text'],'select_count':sum(v for k,v in hist.items() if k.startswith('select ')),'names':dict(ns),'sample':sample,'parameter_samples':ps})
(WORK/'elements.json').write_text(json.dumps(records,ensure_ascii=False),encoding='utf-8')
summary={'seen_bytes':len(blob),'scene_count':len(toc),'indexed_end':end,'unindexed_tail_bytes':len(blob)-end,'scene_versions':[10002],'histogram':dict(histogram),'parameter_histogram':dict(params),'message_opcode_samples':msgsamples,'scenes':scenes}
(WORK/'inspection.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:summary[k] for k in ('seen_bytes','scene_count','indexed_end','unindexed_tail_bytes','scene_versions')},ensure_ascii=False))
print('ELEMENTS',sum(histogram.values()),'TEXT RECORDS',histogram['text'])
print('ALL SCENES DECOMPRESSED AND PARSED; details: inspection.json')
