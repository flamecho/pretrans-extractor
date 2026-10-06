import sys, re, os
import UnityPy
JP=re.compile(rb'(?:[\xe3\xe4\xe5\xe6\xe7\xe8\xe9][\x80-\xbf]{2}|[\xef][\xbc-\xbd][\x80-\xbf]){4,}')
def runs(b):
    out=[]
    for m in JP.finditer(b):
        try: out.append(m.group().decode('utf-8'))
        except: pass
    return out
def do(path):
    env=UnityPy.load(path)
    total=0; samples=[]
    for obj in env.objects:
        try: raw=obj.get_raw_data()
        except Exception: continue
        rs=runs(raw)
        if rs:
            total+=len(rs)
            if len(samples)<8 and max(len(x) for x in rs)>=8:
                samples.append((obj.type.name, max(rs,key=len)))
    return total, samples
if __name__=='__main__':
    for p in sys.argv[1:]:
        try:
            t,s=do(p)
            print('=== %s  jp_runs=%d ==='%(os.path.basename(p),t))
            for tn,st in s: print('   %s : %s'%(tn, st[:80]))
        except Exception as e:
            print('=== %s ERROR %s ==='%(p,e))
