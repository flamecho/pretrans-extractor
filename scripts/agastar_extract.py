"""アガスターシェルゴサ v3.55: consume the packaged Tyrano native parser's tokens.

L0: kag.parser.js, kag.tag.js, kag.tag_ext.js, scenario/system/macro.ks.
This driver handles source branches, display macros and CSV dictionary, not ASAR.
ASAR must be unpacked using @electron/asar; tokens produced with agastar_tokenize.cjs.
"""
from pathlib import Path
from html.parser import HTMLParser
import argparse, collections, hashlib, json, re

TITLE='[PC-JP]アガスターシェルゴサ'
PREFIX='data/scenario/'

class HtmlText(HTMLParser):
    def __init__(self, omit_small=False):
        super().__init__(convert_charrefs=True); self.parts=[]; self.small=0; self.omit_small=omit_small
    def handle_starttag(self,tag,attrs):
        if tag=='small':self.small+=1
        if tag=='img':
            alt=dict(attrs).get('alt','')
            if alt:self.parts.append(alt)
    def handle_endtag(self,tag):
        if tag=='small':self.small=max(0,self.small-1)
    def handle_data(self,s):
        if not(self.omit_small and self.small):self.parts.append(s)
    def value(self):return ''.join(self.parts).replace('\r','').replace('\n','')

def html_text(s,title=False):
    p=HtmlText(title);p.feed(s);p.close();return p.value()

class Extractor:
    def __init__(self,tokens,app):
        self.tokens=tokens;self.app=app;self.rows=[];self.sources=[]
        self.count=collections.Counter();self.files={};self.disposition=collections.Counter()
        self.jnames={};self.macros={};self.used=set();self.tips=[];self.defects=[]
        self.events=[];self.speaker='';self.speaker_visible=False;self.buf=[];self.parts=[]
        self.pending_choices=[];self.refs=set();self.expressions={'f.heroin':'ロア','sf.heroin':'ロア'}
        self.overrides={};self.aliases=set();self.page_serial=0;self.current=''
        for n,a in tokens.items():
            for i,t in enumerate(a):
                if t['name']=='chara_new':self.jnames[t['pm']['name']]=t['pm'].get('jname','')
                if t['name']=='macro':
                    j=next(j for j in range(i+1,len(a)) if a[j]['name']=='endmacro')
                    self.macros[t['pm']['name']]=(n,a[i+1:j])
        self.original_jnames=self.jnames.copy()
        # Source-proven transitive clear/visibility macros. Never based on text shape.
        self.clear_macros={'wd','wd_s','wdd','setup','好感度','チャプター終了処理','過去回想','回想終了',
                           '画面切り替え','フラッシュバック','時間経過','時間経過:夜昼','時間経過:昼夜',
                           '視点変更','視点変更削除','タイトルに戻る','タイトルに戻るノーリセット'}
        self.linefix={}

    def expression(self,s):
        s=s.strip()
        if s.startswith('&'):s=s[1:].strip()
        # Only source assignments and literal concatenation; reject unresolved expressions.
        if s in self.expressions:return self.expressions[s]
        terms=re.findall(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|[a-z]+\.[a-z_]+|\+",s)
        if ''.join(terms).replace(' ','')!=s.replace(' ',''):raise ValueError('Unknown expression '+s)
        result=[]
        for term in terms:
            if term=='+':continue
            if term.startswith(('"',"'")):result.append(term[1:-1])
            elif term in self.expressions:result.append(self.expressions[term])
            else:raise ValueError('Unassigned expression '+term)
        return ''.join(result)

    def value(self,s):return self.expression(s) if s.startswith('&') else s

    def add(self,s,source,kind='text',name=None):
        if not s:return
        assert '\r' not in s and '\n' not in s,(source,s)
        self.used.add(source)
        self.disposition[kind]+=len(s)
        self.buf.append((s,source,self.speaker if name is None else name,self.speaker_visible if name is None else True))

    def format_segment(self,buf):
        # Name applies only to dialogue/thought tokens, never narration. Partial click
        # segments keep original punctuation; quote balance never determines boundaries.
        s=''.join(x[0] for x in buf)
        first=next((x for x in buf if x[0].strip()),None)
        name=first[2] if first and first[3] else ''
        if name and s.lstrip().startswith(('「','『','（','［')):s=name+s
        return s

    def segment(self,reason):
        self.count['click_'+reason]+=1 if reason in ('p','l','macro_p','macro_l') else 0
        if self.buf:
            if reason=='automatic':self.count['automatic_segments']+=1
            self.parts.append((self.format_segment(self.buf),[x[1] for x in self.buf]))
            self.buf=[]
        else:self.count['empty_'+reason]+=1

    def emit(self,s,src,kind):
        s=self.linefix.get(s,s)
        if not s:return
        self.rows.append(s);self.sources.append({'sources':src,'kind':kind,'file':self.current,'page':self.page_serial})
        self.count[kind]+=1

    def page(self,reason,flush=True):
        if self.buf and flush:self.segment('automatic')
        if not self.parts:return
        self.page_serial+=1;self.count['pages']+=1
        self.count['page_reason_'+reason]+=1
        for s,src in self.parts:self.emit(s,src,'segment')
        if len(self.parts)>1:
            self.emit(''.join(x[0] for x in self.parts),sum((x[1] for x in self.parts),[]),'merged')
            self.count['multi_pages']+=1
        self.count['page_clicks_'+str(len(self.parts))]+=1
        self.parts=[]

    def standalone(self,s,source,kind):
        self.page(kind)
        self.used.add(source);self.disposition[kind]+=len(s)
        self.page_serial+=1;self.emit(s,[source],kind)

    def set_name(self,name):
        name=self.value(name)
        self.speaker=self.jnames.get(name,name);self.aliases.add(self.speaker)

    def process(self,n,a=None,stop_return=False,depth=0):
        if depth>8:raise ValueError('recursive subroutine '+n)
        a=self.tokens[n] if a is None else a
        script=False;macro_depth=0;html=False
        for idx,t in enumerate(a):
            tag=t['name'];pm=t['pm'];line=t.get('line',pm.get('line',0))+1
            source=f'{n}:{line}:{t.get("_index",idx)}'
            self.refs.add(n)
            self.events.append((source,tag))
            if tag=='macro':macro_depth+=1;continue
            if tag=='endmacro':macro_depth-=1;continue
            if macro_depth:continue
            if tag=='iscript':script=True;continue
            if tag=='endscript':script=False;continue
            if script:continue
            if tag=='html':html=True;continue
            if tag=='endhtml':html=False;continue
            if html:continue
            if tag=='text':
                if n==PREFIX+'levi/levi7.ks' and line==1886:
                    assert t['val']==']'
                    self.count['excluded_syntax_records']+=1
                    self.disposition['excluded_syntax']+=1
                    continue
                self.add(t['val'],source);continue
            if tag=='ロア':self.add('ロア',source,'name_insert');continue
            if tag=='emb':self.add(self.expression(pm['exp']),source,'embedded');continue
            if tag=='eval':
                exp=pm.get('exp','')
                m=re.fullmatch(r'tf\.name\s*=\s*(.+)',exp)
                if m:self.expressions['tf.name']=self.expression(m.group(1))
                continue
            if tag=='chara_ptext':self.set_name(pm.get('name',''));continue
            if tag.endswith('.n') and tag in self.macros:
                mn,body=self.macros[tag]
                nt=next(t for t in body if t['name']=='chara_ptext')
                self.set_name(nt['pm']['name']);self.speaker_visible=True;continue
            if tag=='jname_config':
                key=pm['name'];self.overrides.setdefault(key,self.jnames[key]);self.jnames[key]=self.value(pm['jname']);continue
            if tag=='jname_reset':
                for key in ([pm['name']] if pm.get('name') else list(self.overrides)):
                    if key in self.overrides:self.jnames[key]=self.overrides.pop(key)
                continue
            if tag=='nw':self.speaker_visible=True;continue
            if tag=='nwd':self.speaker='';self.speaker_visible=False;continue
            if tag=='win_full':self.speaker='';self.speaker_visible=False;continue
            if tag=='win_def':self.speaker_visible=False;continue
            if tag in ('p','l'):
                self.segment(tag)
                if tag=='p':self.page(tag,False)
                continue
            if tag in ('cm','ct','er') or tag in self.clear_macros:
                self.page(tag);self.speaker_visible=False;continue
            if tag in ('chara_d','chara_d_wait','chara_wd','fade_out','月の紋章使用','アイテム削除'):
                # Their packaged bodies call wd subject to visibility/parameters.
                if pm.get('wd')!='false' and (tag not in ('chara_d','chara_d_wait') or not pm.get('name')):
                    self.page(tag);self.speaker_visible=False
                continue
            if tag=='呪文詠唱':
                self.add('「Aperi portam」',source,'glyph',self.value(pm.get('name',self.speaker)))
                self.segment('macro_p');self.page(tag,False);continue
            if tag=='月子咆哮':
                self.add('「gyaaooooooooooo！！！！！！！」',source,'glyph','月子')
                self.segment('macro_p');self.page(tag,False);continue
            if tag=='graph':
                key=pm['storage']
                assert key in ('graph_1.png','graph_2.png','graph_2big.png'),(source,key)
                self.add('Aperi portam' if key=='graph_1.png' else 'gyaaooooooooooo！！！！！！！',source,'glyph')
                continue
            if tag=='エンドタイトル':
                self.standalone(self.value(pm['text']),source,'ending_title');self.count['click_macro_l']+=1;continue
            if tag=='場所名表示':self.standalone(self.value(pm['text']),source,'location');continue
            if tag=='win_c':
                # Save recommendation is system UI, all other occurrences are letters,
                # newspaper text and on-screen questions. Structural source exception.
                if n==PREFIX+'common/pro3.ks' and line==692:
                    self.count['excluded_save_warning']+=1;continue
                self.standalone(''.join(self.value(pm.get(k,'')) for k in ('text1','text2')),source,'effect')
                self.count['click_macro_p']+=1;continue
            if tag=='ptext':
                if pm.get('name')=='chara_name_area':continue
                if pm.get('name')=='place_name':self.standalone(self.value(pm.get('text','')),source,'location');continue
                self.add(html_text(self.value(pm.get('text',''))),source,'effect','');continue
            if tag in ('choice1','choice2','glink','glink_pro'):
                text=self.value(pm.get('text',''))
                # A button targeting title/end navigation is a UI action, classified
                # from its destination; retain actual story and profile selections.
                target=pm.get('target','').lstrip('*')
                if target in {'bunki','skipon','skipoff','endend','endtitle','badendend','title','tyutobunki'}:
                    self.count['excluded_navigation']+=1;continue
                if text:self.standalone(html_text(text),source,'choice')
                else:self.count['image_only_choice']+=1
                continue
            if tag=='call':
                dest=PREFIX+pm.get('storage','');target=pm.get('target','').lstrip('*')
                if dest in {PREFIX+'sub/duplication.ks',PREFIX+'sub/scene_recall.ks'}:
                    b=self.tokens[dest];i=next(i for i,t in enumerate(b) if t['name']=='label' and t['pm']['label_name']==target)
                    end=next((i+j for j,t in enumerate(b[i+1:],1) if t['name']=='label'),len(b))
                    self.process(dest,b[i+1:end],True,depth+1)
                continue
            if tag in ('jump','return','s'):
                self.page(tag)
                if tag=='return' and stop_return:return
                continue
            # Formatting, tip/endtip, timing, art and sound never create a text boundary.

    def run(self):
        routes={'common':['pro1','pro2','pro3','tyutoend'],'saif':[f'saif{i}' for i in range(8)]+['saifbad','saifep'],
                'levi':[f'levi{i}' for i in range(8)]+['levibad','leviep'],'cuo':[f'cuo{i}' for i in range(8)]+['cuobad','cuoep'],
                'sol':[f'sol{i}' for i in range(7)]+['solbad','solep'],
                'extra':['profile_saif','profile_levi','profile_cuo','profile_sol','ss_saif','ss_levi','ss_cuo','ss_sol','ss_mag']}
        for group,files in routes.items():
            self.jnames=self.original_jnames.copy();self.overrides={}
            for file in files:
                n=PREFIX+group+'/'+file+'.ks';self.current=n
                start=len(self.rows);start_count=self.count.copy()
                self.speaker='';self.speaker_visible=False
                self.process(n);self.page('eof')
                self.files[n]={'rows':len(self.rows)-start,'segments':self.count['segment']-start_count['segment'],
                               'merged':self.count['merged']-start_count['merged']}
        raw=(self.app/'data/others/plugin/tip/csv/tip_data.csv').read_text(encoding='utf-8-sig')
        lines=raw.splitlines();header=lines[0].split(',')
        self.current='data/others/plugin/tip/csv/tip_data.csv'
        for i,line in enumerate(lines[1:],2):
            if not line:continue
            cells=line.split(',');assert len(cells)==len(header),(i,len(cells))
            data=dict(zip(header,cells));title=html_text(data['title'],True)
            if data['key']=='yogosyu':
                self.count['excluded_glossary_help']+=1
                continue
            for field in ('tip','tip2'):
                if data[field]:
                    self.standalone('【'+title+'】'+html_text(data[field]),f'{self.current}:{i}:{field}','dictionary')
                    self.tips.append((data['key'],field))
        return self.rows

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,default=Path(__file__).resolve().parents[1]/'_work_agastar')
    ap.add_argument('--out',type=Path);a=ap.parse_args()
    root=Path(__file__).resolve().parents[1];w=a.work
    tokens=json.loads((w/'tokens.json').read_text(encoding='utf-8'));e=Extractor(tokens,w/'app');rows=e.run()
    out=a.out or root/'提取结果'/f'{TITLE}.txt';out.parent.mkdir(parents=True,exist_ok=True)
    data=('\ufeff'+'\n'.join(rows)+'\n').encode('utf-8');out.write_bytes(data)
    summary={'counts':dict(e.count),'files':e.files,'chars':sum(map(len,rows)),'rows':len(rows),
             'sha256':hashlib.sha256(data).hexdigest(),'used_sources':len(e.used),'source_character_categories':dict(e.disposition),
             'aliases':sorted(e.aliases),'dictionary':e.tips,'source_files':sorted(e.refs)}
    (w/'extraction_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    (w/'line_sources.json').write_text(json.dumps(e.sources,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k in ('rows','chars','sha256','counts')},ensure_ascii=False))

if __name__=='__main__':main()
