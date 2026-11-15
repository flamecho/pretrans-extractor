from pathlib import Path
import hashlib, json, collections, re, sys
W = Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'_work_agastar'
app = W/'app'
index = json.loads((W/'asar_index.json').read_text(encoding='utf-8'))
audit=[]; decoded=[]
text_ext={'.ks','.js','.ts','.json','.tjs','.txt','.md','.ini','.html','.css','.csv','.svg','.yml','.yaml','.xml'}
for name, meta in index:
    p=app/name
    b=p.read_bytes()
    assert len(b)==meta['size'], name
    h=hashlib.sha256(b).hexdigest()
    if 'integrity' in meta:
        assert meta['integrity']['algorithm']=='SHA256'
        assert h==meta['integrity']['hash'],name
    kind='media/runtime'
    enc=None
    if p.suffix.lower() in text_ext or not p.suffix:
        for enc in ['utf-8-sig','cp932']:
            try: s=b.decode(enc); break
            except UnicodeDecodeError: pass
        else: raise ValueError(name)
        kind='scenario' if p.suffix=='.ks' else 'configuration/plugin/runtime-source'
        decoded.append({'path':name,'encoding':enc,'chars':len(s),'japanese':len(re.findall('[ぁ-んァ-ヶ一-龯]',s))})
    audit.append({'path':name,'bytes':len(b),'sha256':h,'disposition':kind,'encoding':enc})
(W/'app_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
(W/'decoded_inventory.json').write_text(json.dumps(decoded,ensure_ascii=False,indent=2),encoding='utf-8')
print('Read and audited',len(audit),'members',sum(x['bytes'] for x in audit),'bytes;',len(decoded),'text files')
print('scenario paths:')
for x in audit:
    if x['disposition']=='scenario': print(x['path'])
print('Japanese text outside scenarios:')
for x in decoded:
    if not x['path'].endswith('.ks') and x['japanese']>0 and x['path'].startswith('data/'):print(x)
for n in ['kag.parser.js','kag.tag.js','kag.tag_ext.js']:
    s=(app/'tyrano/plugins/kag'/n).read_text(encoding='utf-8-sig')
    out=[]
    if n=='kag.parser.js': out=[s]
    else:
        for key in ['text','l','p','r','cm','ct','er','chara_ptext','emb','ptext','glink','link','s']:
            m=re.search(r'tyrano\.plugin\.kag\.tag\.'+key+r'\s*=.*?(?=tyrano\.plugin\.kag\.tag\.|$)',s,re.S)
            if m:out.append(m.group())
    (W/(n+'.excerpts.txt')).write_text('\n\n'.join(out),encoding='utf-8')
