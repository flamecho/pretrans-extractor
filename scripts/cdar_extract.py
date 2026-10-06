import sys, os
sys.path.insert(0,'tools')
from cdar import CDAR

def extract_all(p, outdir, depth=0, maxdepth=3):
    os.makedirs(outdir, exist_ok=True)
    a=CDAR(p)
    n=0; nested=0
    for i in range(a.count):
        try: d=a.data(i)
        except Exception: continue
        if not d: continue
        if d[:4]==b'CDAR' and depth<maxdepth:
            sub=os.path.join(outdir, '%08d_cdar'%i)
            open(sub,'wb').write(d)
            cn,cq=extract_all(sub, sub+'.d', depth+1, maxdepth)
            n+=cn; nested+=1+cq
            continue
        open(os.path.join(outdir,'%08d.bin'%i),'wb').write(d)
        n+=1
    return n, nested

if __name__=='__main__':
    src, dst = sys.argv[1], sys.argv[2]
    n, nested = extract_all(src, dst)
    print('files=%d nested_cdar=%d -> %s'%(n,nested,dst))
