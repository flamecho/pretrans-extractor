import UnityPy, glob, os, sys, re
D='tmp2/rear/PCSG00663/Media/'
def load_scripts():
    files=sorted(glob.glob(D+'*.assets'))+sorted(glob.glob(D+'level*'))
    out=[]
    for p in files:
        try: env=UnityPy.load(p)
        except Exception: continue
        for o in env.objects:
            if o.type.name!='TextAsset': continue
            dd=o.read()
            sc=dd.m_Script
            if isinstance(sc,bytes):
                for enc in ('utf-8','utf-16'):
                    try: sc=sc.decode(enc); break
                    except: pass
            if not isinstance(sc,str): continue
            if '@talk' not in sc and '@Talk' not in sc: continue
            out.append((getattr(dd,'m_Name','?'), sc))
    return out

def parse(sc):
    lines=sc.splitlines()
    res=[]; i=0
    def is_cmd(l):
        s=l.lstrip()
        return s.startswith(('@','*',';','//')) or s==''
    while i<len(lines):
        ln=lines[i]
        if ln.lstrip().lower().startswith('@talk'):
            i+=1
            buf=[]
            while i<len(lines) and not is_cmd(lines[i]):
                buf.append(lines[i].strip()); i+=1
            t=''.join(buf)
            t=t.replace('[r]','').replace('<r>','').replace('[br]','')
            t=re.sub(r'\[[^\]]*\]','',t)   # residual inline tags
            t=t.strip()
            if t: res.append(t)
        else:
            i+=1
    return res

if __name__=='__main__':
    scripts=load_scripts()
    scripts.sort(key=lambda x:x[0])
    all_lines=[]
    for nm,sc in scripts:
        all_lines.extend(parse(sc))
    with open('リアフェレス.txt','w',encoding='utf-8-sig') as f:
        for t in all_lines: f.write(t+'\n')
    print('scenario TextAssets:', len(scripts), 'lines:', len(all_lines))
