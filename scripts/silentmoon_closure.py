# -*- coding: utf-8 -*-
import struct, re, os, io, collections, argparse
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
ap = argparse.ArgumentParser()
ap.add_argument('--dec', default=os.path.join(VNTRANS_HOME, '_work_silentmoon/dec'))
ap.add_argument('--deliv', default=os.path.join(VNTRANS_HOME, '提取结果/[JP]Silent Moon.txt'))
A = ap.parse_args()
BASE = A.dec
DELIV = A.deliv
out = io.StringIO()
sum_len = 0; stripped = 0; boxes = 0; sc_boxes = 0; sl_boxes = 0; dia = 0; nar = 0
opt = 0; multi = 0; refs = 0; stale = []
per = []
for letter in 'ABCDEFGH':
    lines = [x.decode('cp932') for x in open(os.path.join(BASE,'ACT_%s.txt'%letter),'rb').read().split(b'\r\n')]
    labels = [(i,l) for i,l in enumerate(lines) if l.startswith('***')]
    seen=set(); lb=ld=ln=lm=lo=0
    for pos,lab in labels:
        m = re.match(r'\*\*\*(SC|SL)_([A-Z]\d{4})_(\d+)', lab)
        if not m: continue
        kind, bid, sid = m.groups(); sp='%s_%s.spt'%(bid,sid)
        if sp in seen: continue
        seen.add(sp)
        if not os.path.exists(os.path.join(BASE,sp)): continue
        refs += 1
        b=open(os.path.join(BASE,sp),'rb').read(); n=struct.unpack_from('<I',b,0)[0]
        for k in range(n):
            op,p1,p2,p3,off,c,p6,p7=struct.unpack_from('<8I',b,4+32*k)
            if op!=1: continue
            body=lines[off:off+c]
            if p1!=0x0d: body=body[1:]
            lb+=1; boxes+=1
            if kind=='SL': sl_boxes+=1; lo+=len(body); opt+=len(body)
            else:
                sc_boxes+=1
                if p1!=0x0d: dia+=1; ld+=1
                else: nar+=1; ln+=1
                if len(body)>=2: lm+=1
            sum_len+=sum(len(x) for x in body)
            stripped+=sum(1 for j,x in enumerate(body) if j>0 and x.startswith('\u3000'))
    per.append('  %s: boxes=%d dia=%d nar=%d multi=%d opt=%d'%(letter,lb,ld,ln,lm,lo))
    multi+=lm
allsp=[f for f in os.listdir(BASE) if f.endswith('.spt')]
used=set()
for letter in 'ABCDEFGH':
    for l in open(os.path.join(BASE,'ACT_%s.txt'%letter),'rb').read().split(b'\r\n'):
        m=re.match(rb'\*\*\*(?:SC|SL)_([A-Z]\d{4})_(\d+)', l)
        if m: used.add('%s_%s.spt'%(m.group(1).decode(),m.group(2).decode()))
stale=[s for s in allsp if s not in used]
text=open(DELIV,encoding='utf-8-sig').read()
rows=text.split('\n')[:-1]
out.write('op1 boxes=%d (SC %d / SL %d)\n'%(boxes,sc_boxes,sl_boxes))
out.write('dia=%d nar=%d multiSC=%d options=%d rows=%d\n'%(dia,nar,multi,opt,len(rows)))
out.write('body display lines=%d sum_len=%d stripped_indent=%d => chars=%d\n'%(sum_len-stripped, sum_len, stripped, sum_len-stripped))
out.write('file chars(no BOM, no LF)=%d ; with LF=%d ; +BOM=%d\n'%(len(text)-len(rows), len(text), len(text)+3))
out.write('spt files=%d referenced=%d stale=%s\n'%(len(allsp), refs, stale))
out.write('quote 「=%d 」=%d ; （=%d ）=%d\n'%(text.count('「'),text.count('」'),text.count('（'),text.count('）')))
out.write('\n'.join(per)+'\n')
open('closure.txt','w',encoding='utf-8').write(out.getvalue())
print('ok')
