from pathlib import Path
import sys, json, collections, re, hashlib,argparse
ROOT=Path(__file__).resolve().parent.parent
WORK=ROOT/'_work_happygift'
sys.path.insert(0,str(ROOT/'tools'))
from rl_decomp import read_toc, scenario, decompress
from rl_parse import Parser
from kare_dx_extract import unquote, decompress_audit

class CheckedParser(Parser):
    def read_function(self,start):
        d=self.d;hdr=d[start:start+8]
        mt,mo=hdr[1:3];op=int.from_bytes(hdr[3:5],'little');argc=int.from_bytes(hdr[5:7],'little');ov=hdr[7]
        if (mt,mo,op) not in [(0,2,x) for x in (0,1,2,3,16)]:
            return super().read_function(start)
        p=start+8
        if d[p]==0x28:p+=self.next_expression(p)
        assert d[p]==0x7b;p+=1
        opts=[];blanks=[]
        if d[p]==0x0a:p+=3
        while d[p]!=0x7d:
            while d[p] in (0x2c,0x0a):
                if d[p]==0x0a:blanks.append(p);p+=3
                else:p+=1
            if d[p]==0x7d:break
            if d[p]==0x28:
                p+=1
                while d[p]!=0x29:
                    if d[p]==0x28:p+=self.next_expression(p)
                    eff=d[p];p+=1
                    if eff not in (0x32,0x33) and d[p]!=0x29 and not 0x30<=d[p]<=0x39:p+=self.next_expression(p)
                p+=1
            n=self.next_string(p);assert n>0 or d[p]==0x0a,(start,p)
            opts.append(d[p:p+n]);p+=n
            assert d[p]==0x0a;p+=3
        assert len(opts)==argc,(len(opts),argc,start)
        self.p=p+1
        return 'select',(mt,mo,op,ov,{'opts':opts,'blank_metadata':blanks})
    def next_string(self,p):
        # This compiler directly abuts a01 string and a00 integer varargs.
        # Stop at a typed argument tag; no comma or quotation is inserted.
        d=self.d;end=p;quoted=False
        while end<len(d):
            c=d[end]
            if quoted:
                if c==0x22 and d[end-1]!=0x5c: return end+1-p
            else:
                if end>p and c==0x61 and d[end+1] in (0,1): break
                if c==0x22: quoted=True
                if d[end:end+9]==b'###PRINT(':
                    end+=9;end+=1+self.next_expression(end);continue
                if not (0x81<=c<=0x9f or 0xe0<=c<=0xef or 0x61<=c<=0x7a or 0x41<=c<=0x5a or 0x30<=c<=0x39 or c in (0x20,0x3f,0x5f,0x22,0x5c)):break
            end+=2 if 0x81<=c<=0x9f or 0xe0<=c<=0xef else 1
        return end-p
    def next_data(self,p):
        n=super().next_data(p)
        assert n>0,(p,self.d[p:p+24].hex())
        return n

ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,default=Path(r'C:\AMEDEO\DRFD'));ap.add_argument('--work',type=Path,default=WORK);args=ap.parse_args()
WORK=args.work;WORK.mkdir(exist_ok=True)
SOURCE=args.source
d=(SOURCE/'SEEN.TXT').read_bytes()
toc=read_toc(d)
scenes=[]; elements=[]; hist=collections.Counter(); bad=[]; heads=[]
for sn,(off,ln) in toc.items():
    try:
        assert 80000<=off and off+ln<=len(d)
        hl,v,co,dl,cl,s=scenario(d,off,ln)
        code,used=decompress_audit(s[co:co+cl],dl)
        assert len(code)==dl,(len(code),dl)
        (WORK/'code').mkdir(exist_ok=True)
        (WORK/'code'/f'SEEN{sn:04d}.bin').write_bytes(code)
        p=CheckedParser(code); rows=[]; sh=collections.Counter(); txt=[]; nonascii=[]
        while not p.eof():
            at=p.p; k,val=p.read_element(); assert at<p.p<=len(code),(at,p.p,len(code))
            row={'scene':sn,'offset':at,'end':p.p,'kind':k,'hex':code[at:p.p].hex()}
            if k=='text':
                text=unquote(val)
                row['text']=text;txt.append(text);key='text'
            elif k in ('func','select','goto','gotoif','gotoon','gotocase','gosub'):
                mt,mo,op,ov,extra=val;row['op']=[mt,mo,op,ov]; key=f'{k} {mt}:{mo}:{op}/{ov}'
                if 'opts' in extra:
                    row['options']=[unquote(b) for b in extra['opts']]
                    row['blank_metadata']=extra['blank_metadata']
                if 'params' in extra:
                    row['params']=[b.hex() for b in extra['params']]
                    for b in extra['params']:
                        try:
                            t=b.decode('cp932')
                            if re.search('[ぁ-んァ-ヶ一-龥]',t):nonascii.append({'offset':at,'op':row['op'],'text':t})
                        except UnicodeDecodeError: pass
            else: key=k
            sh[key]+=1;hist[key]+=1;rows.append(row)
        scenes.append({'scene':sn,'off':off,'length':ln,'header':hl,'version':v,'comp_off':co,'dlen':dl,'clen':cl,'consumed':used,'padding_hex':s[co+used:co+cl].hex(),'elements':len(rows),'text_count':len(txt),'source_chars':sum(map(len,txt)),'samples':txt[:3],'histogram':dict(sh),'japanese_params':nonascii})
        elements.extend(rows)
        heads.append({'scene':sn,'header_hex':s[:co].hex()})
        print(sn,'ok',len(code),len(rows),len(txt),repr(txt[:1])[:150],flush=True)
    except Exception as e:
        bad.append({'scene':sn,'error':repr(e),'offset':getattr(locals().get('p'), 'p',None)})
        print(sn,'FAIL',repr(e),flush=True)
result={'source':str(SOURCE),'seen_size':len(d),'seen_sha256':hashlib.sha256(d).hexdigest(),'toc_count':len(toc),'indexed_end':max(o+n for o,n in toc.values()),'histogram':dict(hist),'scenes':scenes,'failures':bad}
(WORK/'inspection.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
(WORK/'elements.json').write_text(json.dumps(elements,ensure_ascii=False),encoding='utf-8')
(WORK/'headers.json').write_text(json.dumps(heads),encoding='utf-8')
print('SUMMARY',json.dumps({'scenes':len(scenes),'failed_count':len(bad),'failed_sample':bad[:4],'hist':hist.most_common(45)},ensure_ascii=False))
assert not bad,(len(bad),bad[:4])
