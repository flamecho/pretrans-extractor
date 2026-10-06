import sys, re, os
# SJIS double-byte run (kana/kanji): lead 0x81-0x9F/0xE0-0xEF, trail 0x40-0x7E/0x80-0xFC
SJIS=re.compile(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]){4,}')
UTF8=re.compile(rb'(?:[\xe3\xe4\xe5\xe6\xe7\xe8\xe9][\x80-\xbf]{2}){4,}')
def scan(b):
    runs=[]
    for m in SJIS.finditer(b):
        try: runs.append(('sjis', m.group().decode('cp932','replace')))
        except: pass
    for m in UTF8.finditer(b):
        try: runs.append(('utf8', m.group().decode('utf-8','replace')))
        except: pass
    return runs
for p in sys.argv[1:]:
    if not os.path.exists(p): print(p,'MISSING'); continue
    b=open(p,'rb').read()
    r=scan(b)
    from collections import Counter
    c=Counter(e for e,_ in r)
    print('=== %-40s size=%d runs=%d %s ==='%(os.path.basename(p),len(b),len(r),dict(c)))
    if r:
        r2=sorted(r,key=lambda x:-len(x[1]))[:4]
        for e,s in r2: print('   %s: %s'%(e, s[:90]))
