"""Check automatic overflow using the read rlvm TextWindow wrapping rules."""
from pathlib import Path
import json,re,collections,struct
R=Path(__file__).resolve().parent.parent;W=R/'_work_dareura'
E=json.loads((W/'elements.json').read_text('utf-8'));F=json.loads((W/'flow.json').read_text('utf-8'));X=json.loads((W/'extraction.json').read_text('utf-8'))
source=(R/'scripts/rlvm-source/string_utilities.cc').read_text('utf-8')
section=source.split('bool IsKinsoku(int codepoint)')[1].split('0x0};')[0]
kinsoku={int(h,16) for h in re.findall(r'0x([0-9a-f]+)',section)}
names={'Ａ':'桜井','Ｂ':'菜々子','Ｃ':'百恵'}
def expand(t):return re.sub(r'＊([Ａ-Ｃ])',lambda m:names[m[1]],t)
by=collections.defaultdict(list)
for e in E:by[e['scene']].append(e)
overflow=[];normal=23*23;extended=normal+24;page_count=0;max_row=0;fontpages=0;hanging=[]
for sn in X['scope']:
    x=0;row=0;size=24;start=None;with_font=False
    def width(c):return (size-1)//2 if ord(c)<127 else size-1
    for e in by[sn]:
        if e['offset'] not in F['reachable'][str(sn)]:continue
        if e['kind']=='text' and not e['text'].startswith('ＳｅｅｎＥｎｄ'):
            t=expand(e['text']);t=re.sub(r'【[^】]*】','',t)
            if t and start is None:start=e['offset']
            for i,c in enumerate(t):
                w=width(c);k=ord(c) in kinsoku or c==' '
                br=False
                if not(k and x+w<=extended):
                    if x+w>normal:br=True
                    elif not k:
                        end=x+w
                        for n in t[i+1:]:
                            if ord(n) in kinsoku:
                                end+=width(n)
                                if end>extended:br=True;break
                            elif n.isascii() and (n.isalpha() or n in "'-"):
                                end+=width(n)
                                if end>normal:br=True;break
                            else:break
                if br:row+=1;x=0
                if row>=3:
                    overflow.append({'scene':sn,'start':start,'offset':e['offset'],'index':i,'text':t,'size':size,'row':row})
                    row=0;x=0
                x+=w;max_row=max(max_row,row)
                if x>normal:hanging.append({'scene':sn,'offset':e['offset'],'char':c,'x':x,'row':row})
        elif e.get('op',[])[:2]==[0,3]:
            op=e['op'][2]
            if op==101:
                if e['op'][3]==1:size=24
                else:
                    b=bytes.fromhex(e['params'][0]);assert b[:2]==b'$\xff';size=struct.unpack_from('<i',b,2)[0];with_font=True
            elif op in (3,201):x=0;row+=1
            elif op in (17,151,152,161,162,210):
                if start is not None:page_count+=1;fontpages+=with_font
                x=0;row=0;start=None;with_font=False
(W/'layout_audit.json').write_text(json.dumps({'pages':page_count,'font_pages':fontpages,'overflows':overflow,'max_row':max_row,'hanging':hanging},ensure_ascii=False,indent=2),'utf-8')
print('LAYOUT',page_count,'FONT PAGES',fontpages,'OVERFLOWS',len(overflow),'SAMPLES',overflow[:5],'HANGING',len(hanging),'MAX ROW',max_row)
assert not overflow
