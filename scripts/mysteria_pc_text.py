"""PC Japanese Mysteria: Camellia LIBP (1024-byte sectors, 4096 alignment), Malie VM.

No source-character normalization. Structural parsing and provenance are retained.
"""
from pathlib import Path
import argparse, collections, csv, hashlib, io, json, mmap, re, struct, sys
import malie_extract as M


def archive_entries(mm, key=11):
    sig, n1, n2, zero = struct.unpack('<4sIII', M.read_decrypt(mm,key,0,16))
    assert sig == b'LIBP' and 0<n1<1000000 and 0<n2<1000000
    raw = M.read_decrypt(mm,key,16,n1*32)
    offsets = struct.unpack('<%dI'%n2,M.read_decrypt(mm,key,16+n1*32,n2*4))
    base = (16+n1*32+n2*4+4095)&~4095
    es=[]
    for i in range(n1):
        a=raw[i*32:(i+1)*32]
        es.append((a[:20].split(b'\0')[0].decode('cp932'),*struct.unpack('<III',a[20:])))
    out=[]; seen=set()
    def walk(prefix,first,count):
        assert 0<=first and first+count<=n1
        for i in range(first,first+count):
            assert i not in seen
            seen.add(i)
            name,flags,oi,size=es[i]; path='/'.join(filter(None,(prefix,name)))
            if flags&0x10000:
                assert oi<n2
                off=base+offsets[oi]*1024
                assert base<=off and off+size<=len(mm),(path,off,size,len(mm))
                out.append((path,off,size))
            else: walk(path,oi,size)
    walk('',0,1)
    assert len(seen)==n1 and len(out)==n2
    return out, {'entries':n1,'files':n2,'alignment':4096,'sector':1024,'data_base':base}


def parse_exec(data):
    pos=0; fields={}
    def read(n):
        nonlocal pos
        assert 0<=n<=len(data)-pos,(pos,n,len(data))
        p=pos;pos+=n;return data[p:pos]
    def u32(): return struct.unpack('<I',read(4))[0]
    def text():
        n=u32()&0x7fffffff;assert n%2==0
        return read(n).decode('utf-16-le').rstrip('\0')
    variables=[]
    for _ in range(u32()):
        name=text();types=[];t=u32()
        while t:
            types.append((t,u32()));t=u32()
        variables.append({'name':name,'types':types,'values':struct.unpack('<4I',read(16))})
    fields['variables']=variables;fields['unknown']=u32()
    fields['functions']=[(text(),u32(),u32(),u32()) for _ in range(u32())]
    fields['labels']=[(text(),u32()) for _ in range(u32())]
    for key in ('vm_data','vm_code'):
        size=u32();fields[key+'_offset']=pos;fields[key]=read(size)
    count=u32();assert count*8<=len(data)-pos
    fields['indices']=[struct.unpack('<II',read(8)) for _ in range(count)]
    size=u32();fields['strings_offset']=pos;fields['strings']=read(size)
    assert pos==len(data),(pos,len(data))
    for off,size in fields['indices']:assert off%2==0 and size%2==0 and off+size<=len(fields['strings'])
    return fields


def instructions(code):
    pc=0
    while pc<len(code):
        op=code[pc];assert op<=0x33,(hex(pc),hex(op))
        size={0:5,1:5,2:5,3:6,4:3,8:5,9:2,10:3,12:5,13:5,17:2,45:5,49:5,51:2}.get(op,1)
        assert pc+size<=len(code)
        arg=None
        if size>=5:arg=struct.unpack_from('<I',code,pc+1)[0]
        elif size in (2,3):arg=struct.unpack_from('<H',code,pc+1)[0] if op==10 else code[pc+1]
        yield pc,op,arg,size
        pc+=size
    assert pc==len(code)


def vm_string(p,off):
    data=p['vm_data'];assert off%2==0 and 0<=off<len(data)
    end=off
    while end+2<=len(data) and data[end:end+2]!=b'\0\0':end+=2
    assert end+2<=len(data)
    return data[off:end].decode('utf-16-le')


def events(p):
    funcs={x[1]:x for x in p['functions']};stack=[];last=None
    bounds=sorted({x[3] for x in p['functions'] if x[3]})+[len(p['vm_code'])]
    argcounts={}
    for name,fid,res,start in p['functions']:
        if not start:continue
        stop=next(x for x in bounds if x>start)
        returns=[arg//4 for pc,op,arg,size in instructions(p['vm_code'][start:stop]) if op==51]
        if returns:argcounts[fid]=returns[-1]
    labelmap=collections.defaultdict(list)
    for name,off in p['labels']:labelmap[off].append(name)
    functionmap=collections.defaultdict(list)
    for name,fid,res,off in p['functions']:
        if off:functionmap[off].append(name)
    current='';labels=[]
    for pc,op,arg,size in instructions(p['vm_code']):
        if pc in functionmap:current=','.join(functionmap[pc]);stack=[]
        if pc in labelmap:
            labels=labelmap[pc]
            yield {'kind':'label','pc':pc,'labels':labels,'function':current}
        if op in (8,13,17):stack.append(('int',arg))
        elif op==15:stack.append(('int',0))
        elif op in (9,10,12):last=arg;stack.append(('str',arg))
        elif op==6:
            if stack:stack[-1]=('unknown',stack[-1][1])
        elif op in (7,14):
            if stack:stack.pop()
        elif op in (20,21,22,23,24,25,26,27,30,31,33,34,35,36,37,38,39,40):
            if len(stack)>=2:
                b=stack.pop();a=stack.pop()
                if a[0]==b[0]=='int':
                    operations={20:lambda:a[1]+b[1],21:lambda:a[1]-b[1],22:lambda:a[1]*b[1],
                                26:lambda:a[1]|b[1],25:lambda:a[1]&b[1],27:lambda:a[1]^b[1],
                                39:lambda:a[1]<<b[1],40:lambda:a[1]>>b[1]}
                    stack.append(('int',operations[op]()&0xffffffff) if op in operations else ('unknown',None))
                else:stack.append(('unknown',None))
        if op in (3,4,45):
            assert arg in funcs,(pc,arg)
            name=funcs[arg][0]
            argc=p['vm_code'][pc+size-1] if op in (3,4) else argcounts.get(arg,0)
            args=stack[-argc:] if argc else []
            if name=='_ms_message':
                assert stack and stack[-1][0]=='int',(pc,stack[-5:])
                idx=stack[-1][1];assert 0<=idx<len(p['indices']),(pc,idx)
                off,ln=p['indices'][idx]
                text=p['strings'][off:off+ln].decode('utf-16-le')
                yield {'kind':'message','pc':pc,'index':idx,'text':text,'function':current,'labels':labels}
            elif name in ('MALIE_NAME','tag','MALIE_LABLE','FrameLayer_SendMessage','System_GetResult','_ms_page','_ms_pause','_ms_clear','_ms_out','_ms_overlap'):
                strings=[vm_string(p,x[1]) for x in args if x[0]=='str']
                yield {'kind':name,'pc':pc,'text':strings[0] if strings else None,'args':args,'function':current,'labels':labels}
            if argc and len(stack)>=argc:del stack[-argc:]
            stack.append(('unknown',None))
        if op in (50,51):stack=[]


def decode(s, name, name_field=False):
    out=[];i=0;stats=collections.Counter()
    while i<len(s):
        c=ord(s[i]);i+=1
        if c==7:
            assert i<len(s)
            sub=ord(s[i]);i+=1;stats[sub]+=1
            if sub in (1,8,12):
                end=s.find('\0',i)
                if end<0:
                    assert name_field and sub==12
                    end=len(s)
                payload=s[i:end];i=end+1
                if sub==1:
                    base,sep,ruby=payload.partition('\n');assert sep
                    out.append(base)
                elif sub==12:
                    assert payload=='1',repr(payload)
                    out.append(name)
            else:assert sub in (4,6,9),sub
        elif c in (0,10):continue
        else:
            assert c>=32,(c,repr(s))
            out.append(chr(c))
    return ''.join(out),stats


def extract(p,es,config,items,out,work):
    name_match=re.search(r'^NAME01=(.*)$',config,re.M);assert name_match
    default=name_match.group(1).rstrip('\r');assert default=='エミリー'
    scope=None;name=None;visibility='visible';rows=[];sources=[];counts=collections.Counter();controls=collections.Counter()
    seen=[];group=None;groups=[];page_cleared=True;pending_chapter=None;title_calls=[]
    def emit(text,source):
        assert text.strip() and '\n' not in text and '\r' not in text
        rows.append(text);sources.append({'line':len(rows),**source})
    for e in es:
        kind=e['kind']
        if kind=='label':
            for label in e['labels']:
                m=re.fullmatch(r'malie_s(\d+)',label)
                if m:scope=int(m.group(1))
        elif kind=='tag':
            text=e['text'] or ''
            m=re.search(r"<msgframe visibility='([^']+)'",text)
            if m:visibility=m.group(1)
            m=re.search(r"<chapter name='([^']+)'",text)
            if m:pending_chapter=(m.group(1),e['pc'])
            m=re.search(r"<cg src='chapterstart\?title=([^']+)'",text)
            if m and scope not in (10,90):
                assert pending_chapter and pending_chapter[0]!='undefined'
                title_calls.append({'title':pending_chapter[0],'asset':m.group(1),'pc':e['pc'],'chapter_pc':pending_chapter[1]})
                emit(pending_chapter[0],{'kind':'chapter_title','pc':e['pc'],'asset':m.group(1),'chapter_pc':pending_chapter[1]})
                counts['chapter_titles']+=1
        elif kind=='MALIE_NAME':name=e['text']
        elif kind=='_ms_clear':page_cleared=True;name=None;counts['clear_calls']+=1
        elif kind=='_ms_page':counts['page_calls']+=1
        elif kind=='_ms_out':counts['out_calls']+=1
        elif kind=='message':
            counts['messages']+=1;seen.append(e['index'])
            assert page_cleared,('uncleared page',e['index'])
            page_cleared=False
            text,ct=decode(e['text'],default);controls.update(ct)
            assert ct[6]==1
            if scope in (10,90):counts['debug_messages']+=1
            elif text=='削除':counts['system_messages']+=1
            else:
                assert visibility=='visible',(e['index'],visibility)
                source={'kind':'message','pc':e['pc'],'index':e['index'],'scope':scope,'speaker_source':name}
                if name is not None:
                    speaker,nct=decode(name,default,True)
                    counts['name_macros']+=nct[12]
                    # Existing quotation and thought punctuation belongs to the
                    # source. Supplement only unquoted speech; never repair or
                    # balance the original brackets across pages.
                    if not any(c in text for c in '「」『』（）'):
                        text='「'+text+'」';counts['supplemented_quotes']+=1
                    else:counts['source_brackets_preserved']+=1
                    text=speaker+text;counts['named_messages']+=1
                emit(text,source);counts['story_messages']+=1
            name=None
        elif kind=='FrameLayer_SendMessage' and e['function']=='maliescenario':
            assert len(e['args'])==4
            command=e['args'][2];assert command[0]=='int'
            if command[1]==115:
                assert group is None
                group={'pc':e['pc'],'scope':scope,'options':[],'wait_pc':None}
            elif command[1]==116:
                assert group is not None and e['text'] is not None
                text,ct=decode(e['text'],default,True)
                group['options'].append({'text':text,'pc':e['pc'],'flags':e['args'][1][1]})
                counts['all_choices']+=1
                if scope in (10,90):counts['debug_choices']+=1
                elif text=='時間切れ':counts['timeout_animation']+=1
                else:
                    emit(text,{'kind':'choice','pc':e['pc'],'scope':scope,'group_pc':group['pc']})
                    counts['choices']+=1
            elif command[1]==117:
                assert group is not None
                group['wait_pc']=e['pc']
            else:assert command[1]==142
        elif kind=='System_GetResult' and e['function']=='maliescenario':
            assert group and group['wait_pc']
            groups.append(group);group=None
    assert group is None and page_cleared
    assert seen==list(range(len(p['indices'])))
    item_rows=list(csv.reader(io.StringIO(items,newline='')))
    for i,row in enumerate(item_rows):
        if not row:continue
        assert len(row)==2
        term,desc=row;desc=desc.replace('\r','').replace('\n','')
        emit('【'+term+'】'+desc,{'kind':'item_glossary','csv_record':i+1})
        counts['item_glossary']+=1
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text('\n'.join(rows)+'\n',encoding='utf-8-sig',newline='\n')
    work=Path(work);work.mkdir(parents=True,exist_ok=True)
    (work/'sources.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in sources),encoding='utf-8')
    summary={'rows':len(rows),'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),
             'counts':dict(counts),'controls':dict(controls),'choice_groups':groups,'chapter_titles':title_calls,
             'exec_sha256':hashlib.sha256(exec_path.read_bytes()).hexdigest()}
    (work/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('choice_groups','chapter_titles')},ensure_ascii=False,indent=2))


def unpack_selected(root,work):
    root=Path(root);work=Path(work);inputs={}
    for archive,members in {'jpn':['system/exec.dat','system/malie.ini'],'game':['extra/item.csv']}.items():
        with (root/'data'/(archive+'.dat')).open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as mm:
            entries,meta=archive_entries(mm)
            (work/(archive+'_inventory.json')).write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf-8')
            for member in members:
                off,size=next((off,size) for name,off,size in entries if name==member)
                path=work/'resources'/archive/member;path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(M.read_decrypt(mm,11,off,size));inputs[member]=path
    return inputs


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('source');ap.add_argument('out');ap.add_argument('work')
    ap.add_argument('--config');ap.add_argument('--items');ap.add_argument('--events',help='Reuse inspected events with matching exec SHA256')
    args=ap.parse_args();work=Path(args.work);work.mkdir(parents=True,exist_ok=True)
    if Path(args.source).is_dir():
        inputs=unpack_selected(args.source,work);exec_path=inputs['system/exec.dat'];config_path=inputs['system/malie.ini'];items_path=inputs['extra/item.csv']
    else:
        exec_path=Path(args.source);assert args.config and args.items
        config_path=Path(args.config);items_path=Path(args.items)
    p=parse_exec(exec_path.read_bytes())
    if args.events:
        es=[json.loads(line) for line in Path(args.events).read_text(encoding='utf-8').splitlines()]
        assert [e['text'] for e in es if e['kind']=='message']==[p['strings'][o:o+n].decode('utf-16-le') for o,n in p['indices']]
    else:es=list(events(p))
    with items_path.open(encoding='cp932',newline='') as items_file:
        extract(p,es,config_path.read_text(encoding='cp932'),items_file.read(),args.out,work)
