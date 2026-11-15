# -*- coding: utf-8 -*-
# 用 cp932 双字节正则扫描内存 dump，提取日文字符串（自动对齐，不受前缀字节影响）
import glob, os, re
PAT=re.compile(rb'(?:[\x81-\x9f\xe0-\xfc][\x40-\xfc])+')
def jp(c): return 0x3040<=ord(c)<=0x30ff or 0x4e00<=ord(c)<=0x9fff
res=[]
for fn in sorted(glob.glob('mem/*.bin')):
    b=open(fn,'rb').read(); base=int(os.path.basename(fn)[:-4],16)
    for m in PAT.finditer(b):
        raw=m.group(0)
        if len(raw)<6: continue
        try: s=raw.decode('cp932')
        except Exception: continue
        n=sum(1 for c in s if jp(c))
        if n<2 or n < len(s)*0.5: continue
        if any(0xff61<=ord(c)<=0xff9f for c in s): continue
        res.append((base+m.start(),s))
print('原始命中',len(res))
seen={};
for off,s in res:
    if s not in seen or off<seen[s]: seen[s]=off
items=sorted(((o,s) for s,o in seen.items()))
print('去重后',len(items))
with open('mem_text.txt','w',encoding='utf-8',newline='\n') as f:
    for o,s in items: f.write('%08x\t%s\n'%(o,s))
for o,s in items[:6]: print(' ',hex(o),s[:44])
print('--- 目标 ---')
for o,s in items:
    if '原田奈緒' in s: print(' ',hex(o),s)
