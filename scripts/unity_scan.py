import sys, re, os
import UnityPy
jp=re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')

def scan_bytes(b):
    for enc in ('utf-8','utf-16-le','cp932'):
        try: t=b.decode(enc)
        except: continue
        c=len(jp.findall(t))
        if c>=5: return enc,c,t
    return None

def do(path):
    env=UnityPy.load(path)
    hits=[]; n_text=0
    for obj in env.objects:
        tn=obj.type.name
        if tn=='TextAsset':
            d=obj.read()
            try:
                data=d.m_Script
            except Exception:
                data=None
            if data is None:
                try: data=str(d.text).encode('utf-8','ignore')
                except Exception: data=b''
            n_text+=1
            r=scan_bytes(data if isinstance(data,(bytes,bytearray)) else bytes(data))
            if r: hits.append(('TextAsset',getattr(d,'m_Name','?'),r[0],r[1],r[2]))
        elif tn in ('MonoBehaviour',):
            try: raw=obj.get_raw_data()
            except Exception:
                continue
            r=scan_bytes(raw)
            if r and r[1]>=10: hits.append(('MonoBehaviour',getattr(obj,'path_id','?'),r[0],r[1],r[2]))
    return n_text, hits

if __name__=='__main__':
    for p in sys.argv[1:]:
        try:
            n,h=do(p)
            print('=== %s  TextAssets=%d  hits=%d ==='%(os.path.basename(p),n,len(h)))
            for tn,name,enc,c,t in h[:6]:
                i=jp.search(t).start()
                print('   %s %s %s jp=%d  %r'%(tn,name,enc,c,t[i:i+70]))
        except Exception as e:
            print('=== %s ERROR %s ==='%(p,e))
