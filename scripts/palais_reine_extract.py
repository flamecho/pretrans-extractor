#!/usr/bin/env python3
"""Palais de Reine (PS2 JP, SLPM-66817) compiled native-script text extractor.

Decode only strings passed by compiled scenario functions to text/choice handlers.
Keep original printf templates when --dynamic templates is explicitly selected.
No font, menu resource, executable-wide string dump, media OCR, or external lookup.
"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
from pathlib import Path
import struct
import json
import collections

ROOT=Path(os.environ.get('VNTRANS_HOME', os.getcwd()))
DELTA=0xfff80
DATA=b''
TEXT_END=0x640080
MESSAGE=0x13f180
CHOICE=0x13ee40
DISPLAY=0x13ed40
FORMAT=0x1f2640
WAIT=0x13e950
TIMED=0x13e8c0
WRAPPERS={0x234010,0x24eb60}
TARGETS={MESSAGE,CHOICE,DISPLAY,FORMAT,WAIT,TIMED,*WRAPPERS}
VOLATILE={1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,24,25}

def run(start=0x100000,end=TEXT_END,symbolic=False):
    reg={0:0}
    records=[]
    pending=None
    function=start
    memory={}
    for va in range(start,end,4):
        o=va-DELTA
        w=struct.unpack_from('<I',DATA,o)[0]
        op,rs,rt,rd,fn,imm=w>>26,(w>>21)&31,(w>>16)&31,(w>>11)&31,w&63,w&65535
        si=imm if imm<32768 else imm-65536
        if op==9 and rs==29 and rt==29 and si<0:
            reg={0:0,29:0xf0000000} if symbolic else {0:0}
            memory={}
            function=va
        if op==15:
            reg[rt]=imm<<16
        elif op in (8,9,24,25):
            reg[rt]=((reg[rs]+si)&0xffffffff) if isinstance(reg.get(rs),int) else None
        elif op==13:
            reg[rt]=(reg[rs]|imm) if isinstance(reg.get(rs),int) else None
        elif op==12:
            reg[rt]=(reg[rs]&imm) if isinstance(reg.get(rs),int) else None
        elif op==0 and fn in (0x21,0x2d,0x25):
            if isinstance(reg.get(rs),int) and isinstance(reg.get(rt),int):
                reg[rd]=((reg[rs]+reg[rt]) if fn!=0x25 else (reg[rs]|reg[rt]))&0xffffffff
            elif reg.get(rt)==0:
                reg[rd]=reg.get(rs)
            elif reg.get(rs)==0:
                reg[rd]=reg.get(rt)
            else:
                reg[rd]=None
        elif op==0 and fn==0:
            reg[rd]=((reg[rt]<<((w>>6)&31))&0xffffffff) if isinstance(reg.get(rt),int) else None
        elif op in (0x20,0x21,0x23,0x24,0x25,0x37,0x1e):
            address=(reg[rs]+si)&0xffffffff if isinstance(reg.get(rs),int) else None
            reg[rt]=memory.get(address) if symbolic and address in memory else None
        elif symbolic and op in (0x2b,0x3f) and isinstance(reg.get(rs),int):
            memory[(reg[rs]+si)&0xffffffff]=reg.get(rt)
        if pending and va==pending[0]+4:
            call_at,target=pending
            args=[reg.get(i) for i in range(4,12)]
            if target in TARGETS:
                records.append({'at':call_at,'function':function,'target':target,
                                'args':args})
            result=None
            if symbolic and target==FORMAT:
                result={'format':args[1],'at':call_at,'params':args[2:],
                        'extra':[memory.get((reg.get(29,0)+i*8)&0xffffffff) for i in range(9)]}
                if isinstance(args[0],int):
                    memory[args[0]]=result
            for r in VOLATILE:
                reg.pop(r,None)
            reg[2]=result
            pending=None
        if op==3:
            pending=(va,(w&0x3ffffff)<<2)
        elif op==0 and fn==9:
            pending=(va,-1)
        reg[0]=0
    return records

def string(va):
    if va==0:
        return ''
    o=va-DELTA
    if not 0<=o<len(DATA):
        raise ValueError(hex(va))
    z=DATA.index(b'\0',o)
    return DATA[o:z].decode('cp932','strict')


import struct
import json
import collections


def word(va):
    return struct.unpack_from('<I',DATA,va-DELTA)[0]

def repair(rows):
    grouped=collections.defaultdict(list)
    for r in rows:
        if r['target'] in (MESSAGE,CHOICE) and any(r['args'][i] is None for i in ((1,3,4,5) if r['target']==MESSAGE else (1,2,3))):
            grouped[r['function']].append(r)
    functions=sorted(grouped)
    all_starts=[va for va in range(0x100000,TEXT_END,4)
                if word(va)>>16==0x27bd and word(va)&0x8000]
    ends={a:b for a,b in zip(all_starts,all_starts[1:]+[TEXT_END])}
    repaired=[]
    for fun in functions:
        queries=grouped[fun]
        if not queries:
            continue
        end=ends[fun]
        succ={va:[va+4] for va in range(fun,end,4)}
        call_delay={}
        for va in range(fun,end-4,4):
            w=word(va);op=w>>26;rs=(w>>21)&31;fn=w&63
            if op in (4,5,6,7,1,20,21,22,23) or (op==17 and rs==8):
                imm=w&65535;si=imm if imm<32768 else imm-65536
                target=va+4+si*4
                likely=op>=20 or (op in (1,17) and (w>>16)&31 in (2,3,18,19))
                succ[va]=[va+4,va+8] if likely else [va+4]
                succ[va+4]=[target] if likely else [target,va+8]
            elif op==2:
                succ[va+4]=[(w&0x3ffffff)<<2]
            elif op==3 or (op==0 and fn==9):
                call_delay[va+4]=va
            elif op==0 and fn==8:
                succ[va+4]=[]
        pred=collections.defaultdict(list)
        for va,xs in succ.items():
            for x in xs:
                if fun<=x<end:
                    pred[x].append(va)

        def solve(va,reg,ignore_call,seen=frozenset()):
            if reg==0:
                return {0}
            key=(va,reg)
            if key in seen or len(seen)>120:
                return set()
            seen=seen|{key}
            out=set()
            for pv in pred.get(va,[]):
                w=word(pv);op=w>>26;rs=(w>>21)&31;rt=(w>>16)&31;rd=(w>>11)&31;fn=w&63
                imm=w&65535;si=imm if imm<32768 else imm-65536
                defined=False
                val=set()
                if op==15 and rt==reg:
                    val={imm<<16};defined=True
                elif op in (8,9,24,25) and rt==reg:
                    val={(x+si)&0xffffffff for x in solve(pv,rs,ignore_call,seen)};defined=True
                elif op in (12,13) and rt==reg:
                    val={(x&imm) if op==12 else (x|imm) for x in solve(pv,rs,ignore_call,seen)};defined=True
                elif op==0 and fn in (0x21,0x2d,0x25) and rd==reg:
                    aa=solve(pv,rs,ignore_call,seen);bb=solve(pv,rt,ignore_call,seen)
                    val={((a+b) if fn!=0x25 else a|b)&0xffffffff for a in aa for b in bb};defined=True
                elif op==0 and fn==0 and rd==reg:
                    val={(x<<((w>>6)&31))&0xffffffff for x in solve(pv,rt,ignore_call,seen)};defined=True
                elif op in (0x20,0x21,0x23,0x24,0x25,0x37,0x1e) and rt==reg:
                    defined=True
                if defined:
                    out.update(val)
                elif pv in call_delay and call_delay[pv]!=ignore_call and reg in VOLATILE:
                    pass
                else:
                    out.update(solve(pv,reg,ignore_call,seen))
            return out
        for r in queries:
            for i in ((1,3,4,5) if r['target']==MESSAGE else (1,2,3)):
                if r['args'][i] is not None:
                    continue
                vals=solve(r['at']+8,i+4,r['at'])
                if len(vals)==1:
                    r['args'][i]=next(iter(vals))
                    repaired.append({'at':r['at'],'arg':i,'value':r['args'][i]})
    return repaired


import argparse
import hashlib
import re

SCRIPT_START=0x18e600
DEBUG_FORMATS={0x23e5b0,0x23e720,0x23f65c,0x23f7bc,0x23f928,0x23fd54,
               0x2409c8,0x240b0c,0x557eac,0x557f30,0x560684}
DEBUG_WRAPPERS={0x557eb8,0x557f3c,0x560690}

def resolve_field(value):
    if isinstance(value,dict):
        ptr=value['format']
        return {'pointer':ptr,'text':string(ptr),'format_call':value['at'],
                'dynamic':bool(re.search(r'%(?:\d+\$)?[-+ #0]*\d*(?:\.\d+)?[sd]',string(ptr)))}
    if value is None or value>=0xe0000000:
        return {'pointer':None,'text':None,'dynamic':True}
    return {'pointer':value,'text':string(value),'dynamic':False}

def flat(text):
    return text.replace('\r','').replace('\n','')

def name_body(name,body):
    name=name.strip(' \u3000\r\n\t')
    if not name:
        return body
    if body.startswith(('「','『','（','(')):
        return name+body
    return name+'「'+body+'」'

def collect(calls,dynamic):
    items=[]
    for r in calls:
        if r['at']<SCRIPT_START or r['target'] not in (MESSAGE,CHOICE,0x24eb60):
            continue
        item={'address':r['at'],'file_offset':r['at']-DELTA,'function':r['function'],
              'handler':r['target'],'line_numbers':[]}
        if r['target']==MESSAGE:
            item['kind']='message'
            if r['function']==0x24eb60:
                item.update(status='forwarded_wrapper',reason='text supplied at caller; wrapper expanded separately')
            elif r['at']==0x242d30:
                item.update(status='excluded',reason='runtime enumeration of character names from outside scripts')
            else:
                fields=[resolve_field(r['args'][i]) for i in (1,3,4,5)]
                item['fields']=fields
                if any(f.get('format_call') in DEBUG_FORMATS for f in fields):
                    item.update(status='excluded',reason='debug event/condition/status display')
                elif any(f['text'] is None for f in fields):
                    raise ValueError(f'unresolved message {r["at"]:x}: {fields}')
                else:
                    body=''.join(flat(f['text']) for f in fields[1:])
                    item['dynamic']=any(f['dynamic'] for f in fields)
                    if not body.strip():
                        item.update(status='empty',reason='clear text buffers; no added text')
                    elif item['dynamic'] and dynamic=='omit':
                        item.update(status='excluded',reason='dynamic template omitted by selected policy')
                    else:
                        item.update(status='included',texts=[name_body(fields[0]['text'],body)])
        elif r['target']==0x24eb60:
            item['kind']='message_wrapper'
            field=resolve_field(r['args'][1])
            item['fields']=[field]
            item['dynamic']=field['dynamic']
            if r['at'] in DEBUG_WRAPPERS:
                item.update(status='excluded',reason='debug wrapper call; script source verified')
            elif field['text'] is None:
                raise ValueError(f'unresolved wrapper {r["at"]:x}')
            elif item['dynamic'] and dynamic=='omit':
                item.update(status='excluded',reason='dynamic template omitted by selected policy')
            else:
                item.update(status='included',texts=[flat(field['text'])])
        else:
            item['kind']='choice'
            if r['at'] in (0x2f5174,0x2f5198):
                item['table']=0x69ec10
                item['fields']=[resolve_field(v) for v in struct.unpack_from('<14I',DATA,0x69ec10-DELTA)]
                if r['at']==0x2f5174:
                    item.update(status='included',texts=[flat(f['text']) for f in item['fields']],
                                reason='14 script options; runtime availability selects 2 or 3 from same table')
                else:
                    item.update(status='shared_table_variant',reason='same 14 source fields already emitted at 0x2f5174')
            else:
                fields=[resolve_field(r['args'][i]) for i in (1,2,3)]
                item['fields']=fields
                item['dynamic']=any(f['dynamic'] for f in fields)
                if any(f['text'] is None for f in fields):
                    raise ValueError(f'unresolved choice {r["at"]:x}')
                if item['dynamic'] and dynamic=='omit':
                    item.update(status='excluded',reason='dynamic choice omitted by selected policy')
                else:
                    item.update(status='included',texts=[flat(f['text']) for f in fields if f['text'].strip()])
        items.append(item)
    return items

def main():
    global DATA
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source',type=Path,help='SLPM_668.17 from the Japanese PS2 disc')
    ap.add_argument('--dynamic',choices=('templates','omit'),required=True)
    ap.add_argument('--out',type=Path,default=ROOT/'提取结果/[PS2-JP]Palais de Reine.txt')
    ap.add_argument('--evidence',type=Path,default=ROOT/'解析报告/证据/[PS2-JP]Palais de Reine')
    args=ap.parse_args()
    DATA=args.source.read_bytes()
    assert DATA[:4]==b'\x7fELF' and len(DATA)==8450480, 'unsupported executable build'
    assert hashlib.sha256(DATA).hexdigest()=='55ba49185b2ba783401f8ac7e4290e499358bbdfaa5cc6c0c7be9ff423f892c4', 'unsupported executable revision'
    assert word(MESSAGE)==0x27bdff90 and word(CHOICE)==0x27bdffc0
    calls=run(symbolic=True)
    fixes=repair(calls)
    items=collect(calls,args.dynamic)
    lines=[]
    for item in items:
        if item['status']=='included':
            for text in item['texts']:
                assert text and not any(ord(c)<32 for c in text)
                assert not any('\ue000'<=c<='\uf8ff' for c in text)
                item['line_numbers'].append(len(lines)+1)
                lines.append(text)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.evidence.mkdir(parents=True,exist_ok=True)
    args.out.write_text('\n'.join(lines)+'\n',encoding='utf-8-sig',newline='\n')
    out_sha=hashlib.sha256(args.out.read_bytes()).hexdigest()
    stats={'source':str(args.source.resolve()),'source_sha256':hashlib.sha256(DATA).hexdigest(),
           'source_bytes':len(DATA),'mapping_delta':DELTA,'script_start':SCRIPT_START,'script_end':TEXT_END,
           'dynamic_policy':args.dynamic,'output_sha256':out_sha,'lines':len(lines),
           'message_calls':sum(i['kind']=='message' for i in items),
           'choice_calls':sum(i['kind']=='choice' for i in items),
           'wrapper_calls':sum(i['kind']=='message_wrapper' for i in items),
           'message_lines':sum(len(i['line_numbers']) for i in items if i['kind']!='choice'),
           'choice_lines':sum(len(i['line_numbers']) for i in items if i['kind']=='choice'),
           'dynamic_lines':sum(len(i['line_numbers']) for i in items if i.get('dynamic')),
           'branch_arg_repairs':len(fixes),'status_counts':dict(collections.Counter(i['status'] for i in items)),
           'single_click_pages':sum(i['status']=='included' and i['kind']!='choice' for i in items),
           'multi_click_pages':0,'unresolved_fields':0,
           'source_text_fields':sum(len(i.get('fields',[])) for i in items),
           'unique_source_text_pointers':len({f['pointer'] for i in items for f in i.get('fields',[]) if f['pointer']})}
    def save(name,value):
        (args.evidence/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    save('source_map.json',items)
    save('stats.json',stats)
    save('branch_repairs.json',fixes)
    dynamic_rows=[i for i in items if i.get('dynamic') and i['status']=='included']
    save('dynamic_templates.json',dynamic_rows)
    print(json.dumps(stats,ensure_ascii=False,indent=2))
    # Exact source-backed template exceptions; no broad macro exemption.
    exceptions={t for i in dynamic_rows for t in i.get('texts',[])}
    for i in items:
        if i['status']=='included' and i['kind']=='message' and not i['fields'][0]['text'].strip():
            exceptions.update(t for t in i['texts'] if t.startswith(('衣装：','家具：')))
    allow=ROOT/'解析报告/allow/[PS2-JP]Palais de Reine.allow'
    allow.parent.mkdir(parents=True,exist_ok=True)
    allow.write_text('#@dynamic_templates: 用户明确选择保留脚本原有 %s／%d；源地址见 dynamic_templates.json\n'
                     +'#@literal_category_labels: 衣装／家具分类标签是原文正文，名札参数为空；来源见 audit.json\n'
                     +'\n'.join(sorted(exceptions))+'\n',encoding='utf-8',newline='\n')

if __name__=='__main__':
    main()
