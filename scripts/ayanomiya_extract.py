"""Kogado Aya ARCW archive and script extractor. Python 3, standard library."""
from pathlib import Path
import argparse, struct, json, hashlib, re
from collections import Counter, defaultdict

def lzss(data, size):
    ring=bytearray(4096); pos=0xFEE; flags=0; p=0; out=bytearray()
    while len(out)<size:
        flags>>=1
        if not flags&0x100:
            flags=data[p]|0xFF00; p+=1
        if flags&1:
            c=data[p]; p+=1
            out.append(c); ring[pos]=c; pos=(pos+1)&4095
        else:
            a,b=data[p:p+2]; p+=2
            off=a|((b&0xF0)<<4)
            for i in range((b&15)+3):
                c=ring[(off+i)&4095]
                out.append(c); ring[pos]=c; pos=(pos+1)&4095
                if len(out)==size: break
    assert p==len(data), ('unconsumed LZSS data',p,len(data))
    return bytes(out)

def block(data,p):
    length,flags,size=struct.unpack_from('<III',data,p)
    assert flags in (1,2,3), (p,flags)
    body=data[p+12:p+length]
    assert len(body)==length-12
    if flags&1: body=bytes(x^255 for x in body)
    raw=lzss(body,size) if flags&2 else body
    assert len(raw)==size
    return raw,p+length

def probe_archive(path,work):
    data=Path(path).read_bytes()
    magic,version,size,count=struct.unpack_from('<IIII',data)
    assert magic==0xA8BCADBE and version==0 and size==len(data)
    a,p=block(data,16); b,p=block(data,p)
    work=Path(work); work.mkdir(parents=True,exist_ok=True)
    (work/'index1.bin').write_bytes(a); (work/'index2.bin').write_bytes(b)
    print('header',size,count,'idx1',len(a),'idx2',len(b),'data offset',p)
    print('idx1',a[:500].decode('utf-16le',errors='replace'))
    print('idx2',b[:200].hex(' '))

def archive_index(path):
    with Path(path).open('rb') as f:
        head=f.read(16)
        magic,version,size,start=struct.unpack('<IIII',head)
        assert magic==0xA8BCADBE and version==0 and size==Path(path).stat().st_size
        data=head+f.read(start-16)
    names,p=block(data,16); index,p=block(data,p)
    assert p==start
    groups=struct.unpack_from('<I',index)[0]
    result=[]; end=0; ip=4
    for group in range(groups):
        codec,reserved,count,length=struct.unpack_from('<4I',index,ip); ip+=16
        assert reserved==0
        if codec==0: assert length==count*20
        else: assert codec==0x534444  # DDS image driver; no script/config payload.
        for i in range(count):
            no=struct.unpack_from('<I',index,ip+4*i)[0]
            ne=no
            while names[ne:ne+2]!=b'\0\0': ne+=2
            name=names[no:ne].decode('utf-16le')
            if codec==0:
                off,stored,flags,rawsize=struct.unpack_from('<4I',index,ip+count*4+i*16)
                assert off==end and flags in (1,2,3)
                result.append(dict(name=name,offset=start+off,packed=stored-12,raw=rawsize,flags=flags))
                end=off+stored-12
            else:
                assert name.endswith('.dds'), name
                result.append(dict(name=name,codec='DDS'))
        ip+=length
    assert ip==len(index)
    if groups==1: assert start+end==size
    return result

def archive_members(path,selected=None):
    with Path(path).open('rb') as f:
        for info in archive_index(path):
            name=info['name']
            if selected is not None and name not in selected: continue
            if info.get('codec')=='DDS': continue
            f.seek(info['offset']); body=f.read(info['packed'])
            assert len(body)==info['packed']
            if info['flags']&1: body=bytes(x^255 for x in body)
            raw=lzss(body,info['raw']) if info['flags']&2 else body
            assert len(raw)==info['raw']
            yield name,raw,{k:v for k,v in info.items() if k!='name'}

def tokens(s):
    return re.split(r'[ \t]+',s.strip(' \t')) if s.strip(' \t') else []

def parse_script(name,raw):
    text=raw.decode('cp932').replace('\r\r\n','\n').replace('\r\n','\n').replace('\r','\n')
    functions=[]; current=None; pending=None; orphans=[]
    for line,s in enumerate(text.split('\n'),1):
        s=s.split('//',1)[0].strip(' \t')
        if not s: continue
        if s.startswith('$'):
            current=dict(name=tokens(s[1:])[0],declaration=s[1:],line=line,nodes=[])
            functions.append(current); pending=None
        elif s[0] in '{}':
            pending=None
        elif s.startswith('*'):
            assert current is not None,(name,line)
            label_tokens=tokens(s[1:])
            current['nodes'].append(dict(kind='label',label=label_tokens[0] if label_tokens else '',line=line))
            pending=None
        elif s.startswith('@'):
            assert current is not None,(name,line)
            cmd,*args=tokens(s)
            pending=dict(kind='command',cmd=cmd.lower(),args=args,line=line,payload=[])
            current['nodes'].append(pending)
        elif pending is not None:
            pending['payload'].append(dict(line=line,text=s))
        else:
            orphans.append(dict(file=name,line=line,text=s))
    return functions,orphans

def constant_condition(args,constants):
    if 'if' not in args: return True
    cond=args[args.index('if')+1:]
    def value(t):
        if t in constants: return constants[t]
        try:return int(t,0)
        except ValueError:return None
    if len(cond)==1:
        v=value(cond[0]);return None if v is None else bool(v)
    if len(cond)==3:
        a,op,b=cond;a=value(a);b=value(b)
        if a is None or b is None: return None
        if op=='==':return a==b
        if op=='!=':return a!=b
        if op=='<':return a<b
        if op=='<=':return a<=b
        if op=='>':return a>b
        if op=='>=':return a>=b
    return None

def reachable_nodes(fn,constants):
    nodes=fn['nodes'];labels={n['label']:i for i,n in enumerate(nodes) if n['kind']=='label'}
    seen=set();todo=[0];missing=[]
    while todo:
        i=todo.pop()
        if i in seen or i>=len(nodes):continue
        seen.add(i);node=nodes[i]
        if node['kind']=='label':todo.append(i+1);continue
        cmd=node['cmd'];args=node['args'];cond=constant_condition(args,constants)
        if cmd in ('@return','@exit'):
            if cond is not True:todo.append(i+1)
        elif cmd in ('@jump','@jmp'):
            if cond is not False:
                if args and args[0] in labels:todo.append(labels[args[0]])
                else:missing.append(dict(line=node['line'],args=args))
            if cond is not True:todo.append(i+1)
        elif cmd in ('@choose','@cho') and node['payload']:
            for item in node['payload']:
                ts=tokens(item['text'])
                if len(ts)>=2 and constant_condition(ts[2:],constants) is not False:
                    if ts[1] in labels:todo.append(labels[ts[1]])
                    else:missing.append(dict(line=item['line'],args=ts))
            # The selection stores its chosen branch and continues on the following tick.
            todo.append(i+1)
        else:todo.append(i+1)
    return seen,missing

def extract(archive,out,policy_path,audit_dir):
    policy=json.loads(Path(policy_path).read_text(encoding='utf8'))
    members={name:(raw,info) for name,raw,info in archive_members(archive)}
    order=[s.strip(' \t') for s in members['dat/scr/script.def'][0].decode('cp932').replace('\r','').split('\n') if s.strip(' \t')]
    assert set(order)=={name for name in members if name.endswith('.txt')},'script.def scope mismatch'
    raw_const=members['dat/scr/const.def'][0].decode('cp932')
    for key,value in policy['constants'].items():
        assert re.search(re.escape(key)+r','+str(value)+r'(?:\s|$)',raw_const),(key,value)
    rows=[];mapping=[];counts=Counter();byfile=defaultdict(Counter);orphans=[];unresolved=[]
    # Audit covers every @text, @note and @choose command, including rejected content.
    for name in order:
        raw,_=members[name];file=Path(name).name
        funcs,loose=parse_script(file,raw);orphans.extend(loose)
        for fn in funcs:
            reachable,missing=reachable_nodes(fn,policy['constants'])
            unresolved.extend(dict(file=file,function=fn['name'],**item) for item in missing)
            for i,n in enumerate(fn['nodes']):
                if n['kind']!='command' or n['cmd'] not in ('@text','@txt','@note','@not','@choose','@cho'):continue
                cmd=n['cmd'];args=n['args'];payload=n['payload'];speaker=args[0] if args else ''
                text=''.join(v['text'] for v in payload)
                reason=None;values=[];visible_name='';quoted=False
                if i not in reachable and fn['name'] not in policy['preserve_fault_functions']:reason='constant-disabled-or-unreachable'
                elif file in policy['debug_files'] or fn['name'] in policy['debug_functions'] or speaker in policy['debug_speakers']:reason='debug-test'
                elif file in policy['system_files']:reason='system-menu-gallery-version-trial'
                elif fn['name'] in policy['help_functions']:reason='help'
                elif cmd in ('@note','@not'):reason='system-confirmation'
                elif cmd in ('@choose','@cho'):
                    if file in policy['system_choice_files']:reason='system-menu-or-skip'
                    elif not payload:reason='image-choice'
                    else:
                        for item in payload:
                            ts=tokens(item['text'])
                            assert len(ts)>=2,(file,item['line'],ts)
                            if constant_condition(ts[2:],policy['constants']) is not False:values.append(ts[0])
                        reason='choice' if values else 'constant-disabled-choice'
                elif not payload:reason='empty-text'
                elif n['line'] in policy['system_text_nodes'].get(file,[]):reason='system-status-error-confirmation'
                elif file=='99_subroutine.txt' and fn['name'].startswith('派閥'):reason='system-faction-status'
                elif payload[0]['text']=='報告':reason='system-statistic-report'
                else:
                    assert '%' not in text,(file,n['line'],'unresolved-format',text)
                    parts=[v['text'] for v in payload]
                    label=re.fullmatch(r'【([^】]+)】',parts[0])
                    if label and len(parts)>1:
                        visible_name=label[1];parts=parts[1:]
                    if not visible_name and policy.get('include_script_speakers') and speaker not in policy['narration_speakers']:
                        visible_name=speaker
                    body=''.join(parts)
                    dialogue=bool(visible_name) or speaker not in policy['narration_speakers']
                    # Existing quotation and parentheses are source typography.
                    if dialogue and not any(c in body for c in '「」') and not body.startswith('（'):
                        body='「'+body+'」';quoted=True
                    values=[body if visible_name and body.startswith(visible_name) else visible_name+body]
                    reason='dialogue' if dialogue else 'narration'
                output_lines=[]
                for value in values:
                    assert value and '\n' not in value and '\r' not in value
                    rows.append(value);output_lines.append(len(rows))
                counts[reason]+=1;byfile[file][reason]+=1
                mapping.append(dict(file=name,function=fn['name'],command_line=n['line'],cmd=cmd,hidden_speaker=speaker,
                                    visible_name=visible_name,quoted=quoted,payload=payload,disposition=reason,output_lines=output_lines,
                                    preserved_source_fault=fn['name'] in policy['preserve_fault_functions'],
                                    name_source='body-label' if visible_name and label else 'script-speaker' if visible_name else 'none'))
    output=Path(out);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text('\n'.join(rows)+'\n',encoding='utf-8-sig',newline='\n')
    audit=Path(audit_dir);audit.mkdir(parents=True,exist_ok=True)
    with (audit/'source_map.jsonl').open('w',encoding='utf8',newline='\n') as f:
        for m in mapping:f.write(json.dumps(m,ensure_ascii=False)+'\n')
    summary=dict(rows=len(rows),text_commands=sum(m['cmd'] in ('@text','@txt') for m in mapping),
                 choice_rows=sum(len(m['output_lines']) for m in mapping if m['disposition']=='choice'),
                 segment_rows=sum(len(m['output_lines']) for m in mapping if m['disposition'] in ('dialogue','narration')),
                 multi_segment_pages=0,counts=counts,by_file=byfile,name_rows=sum(bool(m['visible_name']) for m in mapping),
                 body_label_rows=sum(m['name_source']=='body-label' for m in mapping),
                 script_speaker_rows=sum(m['name_source']=='script-speaker' for m in mapping),
                 added_quote_rows=sum(m['quoted'] for m in mapping),orphans=orphans,unresolved_local_targets=unresolved,
                 source_sha256=hashlib.sha256(Path(archive).read_bytes()).hexdigest(),
                 output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),script_order=order)
    (audit/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:summary[k] for k in ('rows','text_commands','choice_rows','segment_rows','counts','name_rows','body_label_rows','script_speaker_rows','added_quote_rows')},ensure_ascii=False))

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('archive'); ap.add_argument('--probe'); ap.add_argument('--unpack')
    ap.add_argument('--out'); ap.add_argument('--policy',default=str(Path(__file__).with_name('ayanomiya_policy.json')))
    ap.add_argument('--audit',default='_work_ayanomiya/audit')
    args=ap.parse_args()
    if args.probe: probe_archive(args.archive,args.probe)
    if args.unpack:
        root=Path(args.unpack); root.mkdir(parents=True,exist_ok=True)
        ledger=[]
        for name,raw,info in archive_members(args.archive):
            dest=root/name
            dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(raw)
            ledger.append(dict(name=name,sha256=hashlib.sha256(raw).hexdigest(),**info))
        (root/'manifest.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2),encoding='utf8')
        print('Unpacked',len(ledger),'members',sum(x['raw'] for x in ledger),'bytes')
    if args.out:extract(args.archive,args.out,args.policy,args.audit)
