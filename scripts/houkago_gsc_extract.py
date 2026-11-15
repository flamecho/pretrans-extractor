"""Extract the verified HOUKAGO_KKN XFL/GSC script build, with click/page maps.

Native operand schema and display semantics were verified against houkago_kkn.exe.
Only scr.xfl supplies extracted text. See the accompanying work report.
"""
from pathlib import Path
import argparse, collections, hashlib, itertools, json, re, struct

TITLE = '[PC-JP]放課後は白銀の調べ～急急如律令～'
SOURCE_SHA = 'bc051ec9f086e899971469780ab68874f494aeeb41a0af6269f1aa2d6586bfd8'


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', 'utf-8', newline='\n')


def read_archive(path, schema):
    blob=path.read_bytes()
    assert hashlib.sha256(blob).hexdigest()==SOURCE_SHA, 'Unverified source version'
    magic, directory_size, count=struct.unpack_from('<III',blob)
    assert magic==0x1424c and directory_size==40*count
    base=12+directory_size; scripts=[]; last=0
    for i in range(count):
        at=12+40*i
        name=blob[at:at+32].split(b'\0')[0].decode('cp932')
        rel,size=struct.unpack_from('<II',blob,at+32)
        assert name.endswith('.gsc') and rel==last
        last=rel+size
        data=blob[base+rel:base+rel+size]
        total,hs,cs,isz,ts=struct.unpack_from('<5I',data)
        assert total==size and hs==36 and isz%4==0
        footer=data[hs+cs+isz+ts:]
        array_isz,array_words,label_isz,label_bytes=struct.unpack_from('<4I',data,20)
        assert len(footer)==array_isz+2*array_words+2*label_isz+label_bytes
        assert array_isz%4==0 and label_isz%4==0
        array_index=struct.unpack_from('<'+'I'*(array_isz//4),footer)
        array_data=struct.unpack_from('<'+'H'*array_words,footer,array_isz)
        array_end=0
        for off in array_index:
            assert off==array_end
            array_end=off+1+array_data[off]
        assert array_end==array_words
        label_base=array_isz+2*array_words
        label_index=struct.unpack_from('<'+'I'*(label_isz//4),footer,label_base)
        label_targets=struct.unpack_from('<'+'I'*(label_isz//4),footer,label_base+label_isz)
        label_pool=footer[label_base+2*label_isz:]
        labels=[];label_end=0
        for off,target in zip(label_index,label_targets):
            assert off==label_end
            end=label_pool.index(b'\0',off)
            label=label_pool[off:end].decode('ascii')
            assert not label or label.isdigit()
            labels.append({'label':label,'code_offset':target})
            label_end=end+1
        assert label_end==label_bytes
        indices=struct.unpack_from('<'+'I'*(isz//4),data,hs+cs)
        strings=[]; expected=0; tb=hs+cs+isz
        for n,off in enumerate(indices):
            assert off==expected, (name,n,'unindexed pool bytes')
            end=data.index(b'\0',tb+off,tb+ts)
            raw=data[tb+off:end]
            text=raw.decode('cp932',errors='strict')
            assert '\ufffd' not in text and not any(0xe000<=ord(c)<=0xf8ff for c in text)
            strings.append({'index':n,'pool_offset':off,'file_offset':tb+off,
                            'archive_offset':base+rel+tb+off,'bytes':len(raw),'text':text})
            expected=end+1-tb
        assert expected==ts
        code=data[hs:hs+cs]; pos=0; records=[]
        while pos<cs:
            start=pos; op=struct.unpack_from('<H',code,pos)[0]; pos+=2
            if op&0xf000:
                widths=[2,2] if op&0xf000==0xf000 else [2,2,2]
            else:
                assert str(op) in schema,(name,hex(start),hex(op))
                widths=[2 if t.endswith('16') else 4 for t in schema[str(op)]['inputs']]
            args=[]
            for width in widths:
                args.append(struct.unpack_from('<H' if width==2 else '<I',code,pos)[0]); pos+=width
            records.append({'offset':start,'opcode':op,'args':args,'size':pos-start})
        assert pos==cs
        assert all(x['code_offset'] in {r['offset'] for r in records} for x in labels)
        scripts.append({'name':name,'archive_offset':base+rel,'size':size,'code_size':cs,
                        'sha256':hashlib.sha256(data).hexdigest(),'footer_hex':footer.hex(),
                        'footer_size':len(footer),'array_count':len(array_index),'labels':labels,
                        'strings':strings,'records':records})
    assert base+last==len(blob)
    return scripts


def alias_states(script):
    """Follow local branch paths for the three scenes that initialize $0/$1.

    The repeated predicate is invariant between its name assignment and uses.
    Its two possible outcomes are carried through the graph, so a later test
    can constrain an individual text record to just one of the two names.
    """
    name=script['name']; rr=script['records']; ss=script['strings']
    if name not in ('2504.gsc','2512.gsc','2602.gsc'):return {}
    variable,constant=(1,2) if name=='2602.gsc' else (2900,0)
    assert not any(r['opcode']&0xf000==0x1000 and r['args'][1]==variable for r in rr)
    assert not any(r['opcode']==0x0f for r in rr), 'Check called scene name side effects'
    by={r['offset']:n for n,r in enumerate(rr)}
    result=collections.defaultdict(list)
    for branch_taken in (False,True):
        todo=[(0,())]; seen=set()
        while todo:
            pos,state=todo.pop()
            if pos not in by or (pos,state) in seen:continue
            seen.add((pos,state)); n=by[pos]; r=rr[n]; names=dict(state)
            op=r['opcode']; a=r['args']; nextpos=pos+r['size']
            if op==0x96:names[a[0]]=ss[a[1]]['text']
            if op in (0x51,0x52):
                ix=a[5 if op==0x51 else 4]; raw=ss[ix]['text']
                if re.search(r'\$[0-9]',raw):
                    assert all(int(slot) in names for slot in re.findall(r'\$([0-9])',raw))
                    text=re.sub(r'\$([0-9])',lambda m:names[int(m[1])],raw)
                    entry={'text':text,'slots':names,'predicate_variable':variable,
                           'predicate_constant':constant,'branch_taken':branch_taken}
                    if not any(x['text']==text for x in result[pos]):result[pos].append(entry)
            state=tuple(sorted(names.items()))
            if op==0x10:continue
            if op==0x05:todo.append((a[0],state));continue
            if op in (0x03,0x04):
                matches=(n>=2 and rr[n-2]['opcode']==0x4800
                         and rr[n-2]['args']==[1,variable,constant]
                         and rr[n-1]['opcode']==0xf100 and rr[n-1]['args']==[0,1])
                if matches:todo.append((a[0] if branch_taken else nextpos,state))
                else:todo.extend(((a[0],state),(nextpos,state)))
                continue
            todo.append((nextpos,state))
    return dict(result)


def clean(raw):
    assert not re.search(r'\$[0-9]|@[-@0-9]+|\[|\]|\|',raw),raw
    raw=re.sub(r'\^s[23]', '',raw)
    raw=raw.replace('^m','')
    assert not re.search(r'\^(?!n)',raw),raw
    plate=re.match(r'^【([^】]+)】\^n',raw)
    name=plate[1] if plate else ''
    if plate:raw=raw[plate.end():]
    # Leading spaces after explicit layout breaks are hanging indentation.
    parts=raw.split('^n')
    body=''.join(part.strip(' \u3000') for part in parts)
    return name,body


def extract(scripts,out,evidence):
    out.parent.mkdir(parents=True,exist_ok=True); evidence.mkdir(parents=True,exist_ok=True)
    lines=[]; line_sources=[]; pages=[]; classifications=[]; script_stats=[]; aliases=[]
    counts=collections.Counter(); opcode_counts=collections.Counter(); controls=collections.Counter()

    def emit(text, kind, sources, **extra):
        assert text and '\n' not in text and not any(ord(c)<32 for c in text),text
        lines.append(text); row=len(lines)
        line_sources.append({'line':row,'kind':kind,'sources':sources,**extra})
        return row

    for sc in scripts:
        name=sc['name']; ss=sc['strings']; rr=sc['records']; classification={}
        scene=int(name[:4])>=1000
        for s in ss:
            if not s['text']:classification[s['index']]='empty'
        variants=alias_states(sc)
        for offset, vv in variants.items():aliases.append({'script':name,'code_offset':offset,'variants':vv})
        page=[]; segment=[]

        def source(r,ix):
            s=ss[ix]
            return {'script':name,'code_offset':r['offset'],'opcode':hex(r['opcode']),
                    'string_index':ix,'file_offset':s['file_offset'],
                    'archive_offset':s['archive_offset']}

        def end_segment():
            nonlocal segment
            if segment:page.append(segment); segment=[]

        def end_page():
            nonlocal page
            end_segment()
            if not page:return
            # No macro-bearing scene contains continuation pages in this build.
            hasmacro=any(re.search(r'\$[0-9]',x['raw']) for sg in page for x in sg)
            assert not hasmacro or (len(page)==1 and len(page[0])==1)
            if hasmacro:
                item=page[0][0]; vv=variants[item['record']['offset']]
                for k,v in enumerate(vv):
                    plate,body=clean(v['text'])
                    emit(plate+body,'segment' if k==0 else 'alias_variant',[item['source']],
                         alias_context={key:value for key,value in v.items() if key!='text'})
                    counts['alias_variants' if k else 'segment_lines']+=1
                    counts['macro_expansions']+=1
                counts['pages']+=1; page=[];return
            segment_rows=[]; merged_parts=[]; page_name=''; all_sources=[]
            for sg in page:
                raw=''.join(x['raw'] for x in sg); plate,body=clean(raw)
                if plate:
                    page_name=plate
                    merged_parts.append(plate+body)
                else:merged_parts.append(body)
                text=(plate or page_name)+body
                src=[x['source'] for x in sg];all_sources.extend(src)
                segment_rows.append(emit(text,'segment',src))
                counts['segment_lines']+=1
            if len(segment_rows)>1:
                merged=''.join(merged_parts)
                merged_row=emit(merged,'merged_page',all_sources)
                entry={'segments':segment_rows,'merged':merged_row,
                       'source':name+':'+','.join(hex(x['code_offset']) for x in all_sources)}
                if merged!=''.join(lines[x-1] for x in segment_rows):entry['merged_text']=merged
                pages.append(entry); counts['multi_segment_pages']+=1
            counts['pages']+=1;page=[]

        for r in rr:
            op=r['opcode'];a=r['args'];opcode_counts[f'{op:04x}']+=1
            if op in (0x51,0x52):
                ix=a[5 if op==0x51 else 4]
                assert ix<len(ss)
                if name=='5302.gsc' and ix==1:
                    assert ss[ix]['text']=='★式神02「式神で見る自分」ダミー★'
                    classification[ix]='debug_scene_marker'
                    counts['debug_marker_records']+=1
                    continue
                classification[ix]='story' if scene else 'system_message'
                counts['story_records' if scene else 'system_message_records']+=1
                if not scene:continue
                raw=ss[ix]['text'];controls.update(re.findall(r'\^[a-z][0-9]?',raw))
                if op==0x51:end_page()
                if op==0x52:assert page or segment, (name,r['offset'],'orphan continuation')
                segment.append({'raw':raw,'source':source(r,ix),'record':r})
                if a[-1]:end_page()
            elif op==0x0a:
                end_segment()
            elif op in (0x0b,0x31):
                end_page()
            elif op==0x0e:
                end_page()
                head=a[1];n=a[0];opts=a[7:7+n]
                assert 1<=n<=5
                for k,ix in enumerate([head]+opts):
                    if not ix:continue
                    kind=('choice_heading' if k==0 else 'choice') if scene else 'system_choice'
                    classification[ix]=kind
                    if scene:
                        plate,body=clean(ss[ix]['text'])
                        emit(plate+body,kind,[source(r,ix)])
                        counts['choice_headings' if k==0 else 'choice_lines']+=1
            elif op==0x96:
                classification[a[1]]='name_macro_value'
            elif op==0x79:
                classification[a[1]]='resource_name'
            elif op==0x0f and a[1]:
                classification[a[1]]='script_label'
        end_page()
        remaining=[s for s in ss if s['index'] not in classification]
        assert not remaining, (name,'unclassified script strings',remaining)
        local=collections.Counter(classification.values())
        counts.update({'pool_'+key:value for key,value in local.items()})
        script_stats.append({'name':name,'sha256':sc['sha256'],'size':sc['size'],
                             'code_size':sc['code_size'],'consumed_code_bytes':sum(r['size'] for r in rr),
                             'records':len(rr),'strings':len(ss),'categories':dict(local),
                             'footer_bytes':sc['footer_size'],'array_count':sc['array_count'],
                             'labels':sc['labels']})
        for s in ss:classifications.append({'script':name,**s,'category':classification[s['index']]})

    out.write_text('\n'.join(lines)+'\n','utf-8-sig',newline='\n')
    assert len(lines)==counts['segment_lines']+counts['multi_segment_pages']+counts['alias_variants']+counts['choice_lines']+counts['choice_headings']
    counts['final_rows']=len(lines);counts['scripts']=len(scripts)
    counts['code_bytes']=sum(s['code_size'] for s in scripts)
    counts['opcodes']=sum(opcode_counts.values())
    audit={'title':TITLE,'source_sha256':SOURCE_SHA,'output_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),
           'counts':dict(counts),'controls':dict(controls),'opcode_counts':dict(opcode_counts),
           'unclassified_strings':0,'unconsumed_code_bytes':0,'unindexed_string_bytes':0,
           'scripts':script_stats}
    save_json(evidence/'coverage.json',audit)
    save_json(evidence/'sources.json',line_sources)
    save_json(evidence/'layout.json',{'pages':pages})
    save_json(evidence/'strings.json',classifications)
    save_json(evidence/'aliases.json',aliases)
    print(json.dumps({'output':str(out),'counts':dict(counts),'sha256':audit['output_sha256']},ensure_ascii=False,indent=2))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--schema',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--evidence',type=Path,required=True)
    a=p.parse_args()
    schema=json.loads(a.schema.read_text('utf-8'))
    scripts=read_archive(a.archive,schema)
    extract(scripts,a.output,a.evidence)


if __name__=='__main__':main()
