# -*- coding: utf-8 -*-
import struct, io, json
d=open('gsdb_plain.bin','rb').read()
names=[]
for x in range(0x2400,0x27e0,16):
    t,ln=struct.unpack_from('<HH',d,x)
    off=struct.unpack_from('<I',d,x+4)[0]
    if t==2 and 0x2800<=off<0x2a00:
        names.append(d[off:off+ln].decode('utf-16-le'))
pos=0x3004; m={}
while pos+8<len(d):
    typ,cid=struct.unpack_from('<II',d,pos)
    if typ!=2: break
    j=pos+8; buf=[]
    while j+1<len(d):
        cp=struct.unpack_from('<H',d,j)[0]
        if cp==0: break
        buf.append(chr(cp)); j+=2
    code=''.join(buf); j+=2
    nidx=struct.unpack_from('<I',d,j)[0]; j+=4
    if code.isalpha() and nidx<len(names) and not names[nidx].startswith('***'):
        m[code.upper()]=names[nidx]
    pos=j
m['SAK']='桜子'   # index0 = nameable protagonist; default given name 桜子 (macro/save evidence)
io.open('codemap.json','w',encoding='utf-8',newline='\n').write(json.dumps(m,ensure_ascii=False,indent=1))
print(len(m), m)
