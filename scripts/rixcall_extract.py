import struct, re, os, zlib, sys, json
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

BASE = os.path.join(VNTRANS_HOME, '_work_rixcall')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[JP]The Wind from Rixcall.txt')
RUN = re.compile(rb'\x00([0-9A-Fa-f]{2,8}),')
JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
ANN = re.compile(r'＃＃|■\[|【|→|\[\[|\[[１２３]を選んだ場合\]|\[合流\]|\[達して|\[見ている\]')

def clean_run(t):
    t = t.replace('\r','')
    return t

def realtexts(pay):
    out=[]; i=0
    while True:
        m=RUN.search(pay,i)
        if not m: break
        try: n=int(m.group(1),16)
        except Exception: break
        s=pay[m.end():m.end()+n]; i=m.end()+n
        t=s.decode('cp932','ignore')
        if not JP.search(t): continue
        if '\x00' in t or '本文テキスト' in t or 'Osaka' in t: continue
        out.append(t)
    return out

def parse_mmap(d):
    mm=d.find(b'mmap')
    hl,el,_,cnt=struct.unpack('>HHII',d[mm+8:mm+20])
    ents=[]; off=mm+8+hl
    for k in range(cnt):
        e=d[off:off+el]
        if len(e)<20: break
        ents.append((e[0:4], *struct.unpack('>IIHHI', e[4:20]))); off+=el
    return ents

def from_dir(name):
    p=os.path.join(BASE,'dirs',name+'.dir')
    d=open(p,'rb').read()
    out=[]
    for e in parse_mmap(d):
        if e[0]!=b'XMED': continue
        out += realtexts(d[e[2]+12:e[2]+e[1]])
    return out

def varint(buf,pos):
    val=0
    while True:
        b=buf[pos]; pos+=1; val=(val<<7)|(b&0x7f)
        if not (b>>7): break
    return val,pos

def from_abmp(name):
    d=open(os.path.join(BASE,'pj',name+'.dcr'),'rb').read()
    q=d.find(b'ABMP')+4
    al,q=varint(d,q); end=q+al; ct,q=varint(d,q); ul,q=varint(d,q)
    dec=zlib.decompress(d[q:end]); p=0
    u1,p=varint(dec,p); u2,p=varint(dec,p); rc,p=varint(dec,p)
    res={}
    for i in range(rc):
        rid,p=varint(dec,p); off,p=varint(dec,p); cs,p=varint(dec,p); us,p=varint(dec,p); ct2,p=varint(dec,p)
        tag=dec[p:p+4]; p+=4; res[rid]=(off,cs,us,ct2,tag)
    f=d.find(b'FGEI',end); body=f+4; _,body=varint(d,body)
    out=[]
    for rid in sorted(res):
        off,cs,us,ct2,tag=res[rid]
        if tag!=b'XMED' or off<0: continue
        try: dec2=zlib.decompress(d[body+off:body+off+cs])
        except Exception: continue
        out += realtexts(dec2)
    return out

def filt(lines):
    res=[]
    for t in lines:
        s=clean_run(t)
        if not s.strip(): continue
        if ANN.search(s): continue
        res.append(s)
    return res

FILES=[('0pen','dir'),('4Day','dir'),('5Day','abmp'),('6Day','dir'),('6Day2','dir'),
       ('7Day','dir'),('7Day2','dir'),('7Day3','dir'),('8Day','dir'),('9Day','abmp'),
       ('10Day','dir'),('10Day2','dir'),('10Day3','dir'),('10Day4','dir'),('10Day5','dir'),
       ('BAD','dir')]
stats={}
lines=[]
for name,kind in FILES:
    raw = from_abmp(name) if kind=='abmp' else from_dir(name)
    kept = filt(raw)
    stats[name]=(len(raw),len(kept))
    lines += kept
# Base special
braw=from_dir('Base'); bclean=[clean_run(x) for x in braw]
bstats=[]
for i,x in enumerate(bclean):
    if i in (0,1) or i==len(bclean)-1:
        if x.strip() and not ANN.search(x): lines.append(x); bstats.append(i)
print('per-file raw->kept:', stats)
print('Base kept indices', bstats, 'of', len(bclean))
print('total lines', len(lines))
# unbalanced checks
def unb(s, a, b): return s.count(a) - s.count(b)
print('open quote lines', sum(1 for x in lines if x.count('「')-x.count('」')>0))
print('close quote lines', sum(1 for x in lines if x.count('」')-x.count('「')>0))
print('open paren lines', sum(1 for x in lines if x.count('（')-x.count('）')>0))
print('close paren lines', sum(1 for x in lines if x.count('）')-x.count('（')>0))
print('quote totals', sum(x.count('「') for x in lines), sum(x.count('」') for x in lines))
print('paren totals', sum(x.count('（') for x in lines), sum(x.count('）') for x in lines))
# build output
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT,'wb') as f:
    f.write(b'\xef\xbb\xbf')
    f.write(('\n'.join(lines)+'\n').encode('utf-8'))
print('wrote', OUT, len(lines))
