"""カレと彼の間で DX: reuse rlvm-derived rl_decomp/rl_parse.
L0 evidence: original GAMEEXE.INI WINDOW.000.R_COMMAND_MOD=0 and NAME_MOD=1;
rlvm module_msg.cc Msg_pause/NewPageOnAllAfterLongop, par/HardBrake,
text_window.cc SetNameWithoutDisplay/RenderNameInBox/RenderToScreen. Visible name tags are retained; see report.
"""
from pathlib import Path
import sys,re,json,collections,struct
from rl_decomp import read_toc,scenario,decompress,XOR
from rl_parse import Parser
ROOT=Path(__file__).resolve().parent.parent
TITLE='[PC-JP]カレと彼の間で -DX ツインズパック版-'
def unquote(b):
    # Width-aware literal conversion matching TextoutElement::GetText.
    out=bytearray(); i=0; quoted=False
    while i<len(b):
        c=b[i]
        if c==34: quoted=not quoted; i+=1; continue
        if quoted and c==92 and i+1<len(b) and b[i+1]==34:
            out.append(34); i+=2; continue
        n=2 if 0x81<=c<=0x9f or 0xe0<=c<=0xef else 1
        out.extend(b[i:i+n]); i+=n
    return out.decode('cp932')
def clean(b):
    return unquote(b).replace('＊Ａ','白石').replace('＊Ｂ','瑞穂')
def decompress_audit(src,n):
    out=bytearray(); p=8; bit=256; flag=0
    while len(out)<n:
        if bit==256: flag=src[p]^XOR[p&255]; p+=1; bit=1
        if flag&bit: out.append(src[p]^XOR[p&255]); p+=1
        else:
            v=(src[p]^XOR[p&255])|((src[p+1]^XOR[(p+1)&255])<<8); p+=2
            a=len(out)-(v>>4); count=(v&15)+2
            assert 0<=a<len(out)
            for k in range(count): out.append(out[a+k])
        bit<<=1
    assert len(out)==n
    # Compressor may leave one literal from a partially used flag group.
    return bytes(out),p
def main():
    work=ROOT/'_work_kare'; game=next(work.rglob('SEEN.TXT')).parent
    blob=(game/'SEEN.TXT').read_bytes(); lines=[]; origins=[]; pages=[]; scene_stats=[]
    stats=collections.Counter(); warnings=[]; all_params=[]
    for sn,(off,length) in sorted(read_toc(blob).items()):
        h,v,co,dl,cl,s=scenario(blob,off,length)
        assert v==10002 and co+cl==length
        code=decompress(s[co:co+cl],dl); check,used=decompress_audit(s[co:co+cl],dl)
        assert code==check and len(code)==dl
        p=Parser(code); current=[]; source=[]; start_line=len(lines)
        st={'scene':sn,'offset':off,'stored':length,'code_bytes':dl,'lzss_consumed':used,'compressed':cl,'padding_hex':s[co+used:co+cl].hex(),'text_records':0,'options':0,'halts':0,'name_chars':0,'speaker_chars':0,'speaker_lines':0,'page_count':0}
        def flush(reason,at):
            if not current: return
            t=''.join(current); current.clear()
            nameparts=re.findall(r'【([^】]*)】',t)
            if nameparts: st['name_chars']+=sum(len(x)+2 for x in nameparts)
            t=re.sub(r'【[^】]*】','',t).rstrip()
            speaker=''
            if nameparts:
                # In this game each name tag starts one page and is rendered to screen.
                # The tag-only text element in SEEN7000 is joined before this step.
                assert len(nameparts)==1 and t.startswith(('「','『')), (sn,at,nameparts,t)
                speaker=nameparts[0]; t=speaker+t
                st['speaker_chars']+=len(speaker); st['speaker_lines']+=1
            if t.strip():
                lines.append(t); origin={'scene':sn,'offsets':list(source),'end':at,'reason':reason,'speaker':speaker,'line':len(lines)}
                origins.append(origin); pages.append(origin); st['page_count']+=1
            else: stats['empty_layout_pages']+=1
            source.clear()
        while not p.eof():
            a=p.p; k,val=p.read_element(); assert p.p>a
            stats['elements']+=1
            if k=='text':
                t=clean(val)
                if t.startswith('ＳｅｅｎＥｎｄ'):
                    st['halts']+=1; flush('halt',a); continue
                if sn<100 or sn>=9000:
                    stats['system_text_records']+=1; continue
                current.append(t); source.append(a); st['text_records']+=1
            elif k=='func':
                mt,mo,op,ov,extra=val
                for b in extra.get('params',[]):
                    all_params.append({'scene':sn,'offset':a,'op':[mt,mo,op,ov],'hex':b.hex()})
                if (mt,mo)==(0,3):
                    stats[f'msg_{op}_{ov}']+=1
                    if op in (17,151,152,161,162,210): flush(f'op{op}',a)
                    elif op in (3,201): stats['soft_breaks']+=1
                    elif op in (205,206,207): raise AssertionError('Unhandled click variant')
                    elif op==102: raise AssertionError('Unexpected window change')
            elif k=='select':
                if sn<100 or sn>=9000: stats['system_options']+=len(val[4]['opts']); continue
                if sn==100 and a==0x59:
                    # Debug-only jump menu: intF[1998] guard @0xf; normal path @0x44 -> 0x11f.
                    stats['debug_options']+=len(val[4]['opts']); continue
                flush('select',a)
                for b in val[4]['opts']:
                    t=clean(b).strip(); assert '###PRINT' not in t
                    if t:
                        lines.append(t); origins.append({'scene':sn,'offsets':[a],'line':len(lines),'reason':'option'}); st['options']+=1
            elif k in ('goto','gotoif','gotoon','gotocase','gosub') and current:
                warnings.append({'scene':sn,'offset':a,'kind':k,'pending':list(source)})
        assert p.p==len(code)
        flush('eof',len(code)); st['output_lines']=len(lines)-start_line
        scene_stats.append(st)
    assert len(origins)==len(lines)
    dest=ROOT/'提取结果'/f'{TITLE}.txt'; dest.parent.mkdir(exist_ok=True)
    with dest.open('w',encoding='utf-8-sig',newline='\n') as f:f.write('\n'.join(lines)+'\n')
    result={'title':TITLE,'stats':dict(stats),'scenes':scene_stats,'lines':len(lines),'chars':sum(map(len,lines)),'bytes':dest.stat().st_size,'flow_pending':warnings}
    (work/'extraction-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    (work/'line-origins.json').write_text(json.dumps(origins,ensure_ascii=False),'utf-8')
    (work/'parameter-audit.json').write_text(json.dumps(all_params,ensure_ascii=False),'utf-8')
    print('OUTPUT',dest,'LINES',len(lines),'CHARS',result['chars'],'BYTES',result['bytes'])
    print('FLOW_PENDING',len(warnings),'LZSS_TRAILING',collections.Counter(x['compressed']-x['lzss_consumed'] for x in scene_stats))
    print('STATS',dict(stats))
if __name__=='__main__':main()
