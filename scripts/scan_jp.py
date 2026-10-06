import sys, os, glob, re
SJIS=re.compile(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc])+')
HIRA=re.compile(r'[\u3041-\u309f]')
CAP=8_000_000
def scan_dir(base, limit_read=1_500_000, min_runs=5):
    hits=[]
    files=[f for f in glob.glob(base+'/**/*', recursive=True) if os.path.isfile(f)]
    for fp in files:
        try: sz=os.path.getsize(fp)
        except: continue
        if sz>CAP: continue
        with open(fp,'rb') as f: b=f.read(limit_read)
        good=0; sample=None
        for m in SJIS.finditer(b):
            if len(m.group())<8: continue
            try: t=m.group().decode('cp932')
            except: continue
            if HIRA.search(t) and '\ufffd' not in t:
                good+=1
                if sample is None or len(t)>len(sample): sample=t
        if good>=min_runs: hits.append((fp, sz, good, sample))
    return len(files), hits
if __name__=='__main__':
    base=sys.argv[1]
    n,hits=scan_dir(base)
    print('scanned files:', n, ' text hits:', len(hits))
    for fp,sz,g,s in sorted(hits,key=lambda x:-x[2])[:25]:
        print('  %-52s size=%-9d runs=%-6d %s'%(fp.replace(base+'/',''), sz, g, (s or '')[:60]))
