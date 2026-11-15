"""Extract the bundled Innocentria Lustras 1.7 NScripter script.

Strict CP932 decoding, source provenance, explicit click/page state, choices in
script order, visible names and manually verified narrative image lettering.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,re,math

EXPECTED='b71cf04c73cbc1c83f82b4aeedcc56738d7c052b8405f15c288a24436deb3ab5'
COLOR=re.compile(r'#[0-9a-fA-F]{6}')
RUBY=re.compile(r'\(([^()/]+)/([^()/]+)\)')
NAME=re.compile(r'(?:【[^】]+】)+')
IMAGES={
    'sys\\routeend.jpg':'Route End.',
    'sys\\mornning.jpg':'Next Morning...',
    'sys\\inter_ape01.bmp':'Interval Aperio-01',
    'sys\\inter_ape02.bmp':'Interval Aperio-02',
    'sys\\inter_ka01.bmp':'Interval Kaizel-01',
    'sys\\inter_ka02.bmp':'Interval Kaizel-02',
    'sys\\inter_ka03.bmp':'Interval Kaizel-03',
    'sys\\inter_cra01.bmp':'Interval Craft-01',
    'sys\\inter_cra02.bmp':'Interval Night-01',
    'sys\\inter_cra03.bmp':'Interval Night-02',
    'sys\\inter_cra04.bmp':'Interval Night-03',
    'sys\\inter_cra05.bmp':'Interval Night-04',
    'sys\\hinto2.jpg':'しろじょうヒントコーナー。',
}
VIDEO=[
    ('たとえばそれは、階段を降りる足音のリズムとか注意を惹く時に袖を引っ張るしぐさとかごちそうさまとセットの笑顔とかあなたと共にあることの　幸せ',35.2,40.7),
    ('レール',52.7,54.4),
    ('善悪の定義',53.6,54.8),
    ('記憶を守るなら',54.3,55.3),
    ('臆病者',55.4,56.0),
]

def plain(s):
    s=s.replace('$777','ルミナ')
    s=COLOR.sub('',s)
    s=RUBY.sub(r'\1',s)
    if re.search(r'\$\d+|%\d+|[\ue000-\uf8ff\ufffd]',s):
        raise ValueError('Unresolved text '+s)
    return s

def commands(s):
    """Only split command separators outside quoted resource/text strings."""
    start=0;quoted=False
    for i,ch in enumerate(s):
        if ch=='"':quoted=not quoted
        elif ch==';' and not quoted:
            if s[start:i].strip():yield s[start:i].strip()
            return
        elif ch==':' and not quoted:
            if s[start:i].strip():yield s[start:i].strip()
            start=i+1
    if s[start:].strip():yield s[start:].strip()

def in_scope(n):
    return 2536<=n<40215 or 40355<=n<42868 or 43551<=n<46425

def extract(dat,out,evidence):
    encrypted=dat.read_bytes()
    if hashlib.sha256(encrypted).hexdigest()!=EXPECTED:raise ValueError('Source version changed')
    script=bytes(x^0x84 for x in encrypted).decode('cp932',errors='strict')
    raw=script.splitlines();rows=[];source=[];pages=[];dual=[];excluded=[];stats=Counter();labels={};anomalies=[]
    pending=[];pending_src=[];segments=[];display=[];label='';speaker='';name_line=None;window=[30,3];unreachable=False
    consumed=set();choice_lines=set();max_pages=[]
    def emit(text,kind,linenos,**kw):
        if not text.strip():return
        rows.append(text)
        source.append(dict(output=len(rows),kind=kind,source=linenos,label=label,**kw));stats[kind]+=1
    def click(reason,n):
        if pending:
            value=''.join(pending).strip()
            if value:segments.append(dict(text=value,source=list(pending_src),speaker=speaker,name_source=name_line,click=reason,line=n))
        pending.clear();pending_src.clear()
    def page(reason,n):
        nonlocal speaker,name_line
        click(reason,n)
        if segments:
            pid=len(pages)+1;outputs=[];texts=[]
            for j,s in enumerate(segments):
                prefix=s['speaker'] if j==0 or s['speaker']!=segments[j-1]['speaker'] else ''
                text=prefix+s['text'];emit(text,'body',s['source'],speaker=prefix,name_source=s['name_source'],page=pid)
                outputs.append(len(rows));texts.append(text)
            if len(segments)>1:
                merged=''.join(texts);emit(merged,'merged',[a for s in segments for a in s['source']],page=pid)
                dual.append(dict(segments=outputs,merged=len(rows),merged_text=merged))
            item=dict(page=pid,segments=outputs,boundary=reason,boundary_line=n,window=list(window),display=list(display))
            pages.append(item)
            if len(display)>window[1]:max_pages.append(item)
        segments.clear();display.clear();speaker='';name_line=None
    def text(s,n):
        nonlocal speaker,name_line
        s=plain(s.strip());consumed.add(n);stats['source_text_records']+=1
        if NAME.fullmatch(s):
            speaker=''.join(re.findall(r'【([^】]+)】',s));name_line=n;display.append(dict(line=n,text=s,name=True));stats['name_records']+=1;return
        if n>=45310 and re.match(r'^#[0-9A-Fa-f]{6}',raw[n-1].strip()) and re.fullmatch(r'[^：「」]{1,20}：',s):
            speaker=s[:-1];name_line=n;display.append(dict(line=n,text=s,name=True));stats['name_records']+=1;return
        part=[]
        for ch in s:
            if ch in '\\@':
                if part:display.append(dict(line=n,text=''.join(part)));part.clear()
                if ch=='\\':stats['page_marks']+=1;page('backslash',n)
                else:stats['click_marks']+=1;click('at',n)
            else:
                pending.append(ch);part.append(ch)
                if not pending_src or pending_src[-1]!=n:pending_src.append(n)
        if part:display.append(dict(line=n,text=''.join(part)))
    i=0
    while i<len(raw):
        n=i+1;s=raw[i].strip();i+=1
        if s.startswith('*'):
            label=s[1:].split(';')[0].split()[0];unreachable=False;labels[label]={'line':n,'scope':'story' if in_scope(n) else 'system'};continue
        if s.startswith(';'):continue
        scope=in_scope(n) and not unreachable
        if not s:
            if scope and raw[n-1] and (pending or segments or speaker):display.append(dict(line=n,text='',blank=True))
            continue
        istext=not re.match(r'[A-Za-z_]',s) and not s.startswith((':','~','"'))
        if istext:
            if scope:text(s,n)
            else:
                excluded.append(dict(line=n,label=label,reason='unreachable' if unreachable else 'system',text=s));stats['excluded_records']+=1
            continue
        if not scope:continue
        if s.startswith('select '):
            page('choice',n);data=s;linenos=[n]
            while data.rstrip().endswith(','):
                nxt=raw[i].strip()
                if not nxt.startswith('"'):raise ValueError(f'Malformed multiline choice at {i+1}')
                data+=nxt;i+=1;linenos.append(i)
            items=re.findall(r'"([^"]*)"\s*,\s*\*([A-Za-z0-9_]+)',data)
            if not items:raise ValueError(f'Empty choice at {n}')
            choice_lines.update(linenos);stats['choice_commands']+=1
            for value,target in items:emit(plain(value).strip(),'choice',linenos,target=target)
            unreachable=True;continue
        for cmd in commands(s):
            if cmd.startswith('click'):
                # Native tokenizer consumes the ASCII command separately from
                # immediately adjacent CP932 text, as proven by scanner code.
                click('click_command',n);stats['click_commands']+=1
                tail=cmd[5:].strip()
                if tail:
                    if n not in (44109,44110):raise ValueError(f'Unexpected click operand at {n}')
                    text(tail,n);anomalies.append(dict(line=n,kind='adjacent_click_text',text=cmd))
            elif cmd.startswith('textclear'):
                page('textclear',n)
            elif cmd.startswith('setwindow '):
                page('setwindow',n);match=re.match(r'setwindow\s+[-\d]+,[-\d]+,(\d+),(\d+)',cmd)
                if not match:raise ValueError(f'Bad window at {n}')
                window[:]=[int(match[1]),int(match[2])]
            elif re.match(r'gosub \*winset[123]\b',cmd):
                page('window_subroutine',n);window[:]=[30,3]
            elif cmd.startswith(('goto ','return')):
                page('flow',n)
                if cmd.startswith('goto '):unreachable=True
            elif cmd.startswith('mpegplay '):
                if n!=25648 or 'mov\\op.mpg' not in cmd:
                    raise ValueError(f'Unreviewed narrative movie at {n}')
                page('movie',n)
                for value,start,end in VIDEO:
                    emit(value,'video_text',[n],resource='mov\\op.mpg',time_start=start,time_end=end)
            elif cmd.startswith(('bg ','lsp ')):
                for image_path,value in IMAGES.items():
                    if image_path in cmd:
                        emit(value,'image_text',[n],resource=image_path)
                if cmd.startswith('lsp ') and ':s/' in cmd:
                    m=re.search(r':s/[^;]*;([^\"]*)',cmd)
                    if not m:raise ValueError(f'Bad sprite text at {n}')
                    emit(plain(m[1]).strip(),'effect_text',[n])
    page('eof',len(raw))
    # Name records without a following quoted dialogue need source review.
    for item in source:
        if item.get('speaker') and rows[item['output']-1][len(item['speaker']):].startswith(('「','『','（')) is False:
            anomalies.append(dict(kind='named_nonquote',**item,text=rows[item['output']-1]))
    evidence.mkdir(parents=True,exist_ok=True);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text('\n'.join(rows)+'\n',encoding='utf-8-sig',newline='\n')
    summary=dict(title='[PC-JP]ラストラス',source_sha256=EXPECTED,output_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),rows=len(rows),statistics=dict(stats),pages=len(pages),multi_segment_pages=len(dual),source_lines=len(raw),consumed_text_records=len(consumed),unresolved=0)
    artifacts={'source_map.json':source,'layout_map.json':{'pages':dual},'pages.json':pages,'coverage.json':dict(summary,labels=labels,consumed=sorted(consumed),choice_source_lines=sorted(choice_lines),excluded=excluded),'source_anomalies.json':anomalies,'capacity_candidates.json':max_pages,'summary.json':summary}
    for fn,obj in artifacts.items():(evidence/fn).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2));print('CAPACITY candidates',len(max_pages),max_pages[:2]);print('ANOMALIES',len(anomalies),anomalies[:8])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dat',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--evidence',required=True,type=Path);a=p.parse_args();extract(a.dat,a.out,a.evidence)
