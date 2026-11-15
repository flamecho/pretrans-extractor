# -*- coding: utf-8 -*-
# 内存明文采集器：每轮扫描含日文的可写区块 -> 提取 cp932 串 -> 与 gsce_decrypted.bin 对齐得 (偏移,密钥)
import ctypes, ctypes.wintypes as w, re, os, sys, time, json
PID=int(sys.argv[1]) if len(sys.argv)>1 else 7140
ROUNDS=int(sys.argv[2]) if len(sys.argv)>2 else 1
SLEEP =float(sys.argv[3]) if len(sys.argv)>3 else 10.0
k=ctypes.WinDLL('kernel32',use_last_error=True)
h=k.OpenProcess(0x0410|0x0010,False,PID)
if not h: print('OpenProcess failed'); sys.exit(1)
class MBI(ctypes.Structure):
    _fields_=[('BaseAddress',ctypes.c_void_p),('AllocationBase',ctypes.c_void_p),('AllocationProtect',w.DWORD),
              ('RegionSize',ctypes.c_size_t),('State',w.DWORD),('Protect',w.DWORD),('Type',w.DWORD)]
def regs():
    a=0; m=MBI()
    while a<0x80000000:
        if not k.VirtualQueryEx(h,ctypes.c_void_p(a),ctypes.byref(m),ctypes.sizeof(m)): break
        yield (m.BaseAddress or 0),m.RegionSize,m.State,m.Protect
        a=(m.BaseAddress or 0)+m.RegionSize
        if m.RegionSize==0: break
def rd(base,size):
    buf=ctypes.create_string_buffer(size); got=ctypes.c_size_t(0)
    if k.ReadProcessMemory(h,ctypes.c_void_p(base),buf,size,ctypes.byref(got)): return buf.raw[:got.value]
    return None
PAT=re.compile(rb'(?:[\x81-\x9f\xe0-\xfc][\x40-\xfc])+')
def jp(c): return 0x3040<=ord(c)<=0x30ff or 0x4e00<=ord(c)<=0x9fff
def hira(s): return sum(1 for c in s if 0x3041<=ord(c)<=0x309f)
data=open('gsce_decrypted.bin','rb').read()
T=[bytes([b^k for b in range(256)]) for k in range(256)]
DB='corpus.jsonl'
seen=set()
if os.path.exists(DB):
    for l in open(DB,encoding='utf-8'):
        try: seen.add(json.loads(l)['s'])
        except Exception: pass
print('已存明文',len(seen))
for r in range(ROUNDS):
    t0=time.time(); new=0; aligned=0
    for base,size,state,prot in regs():
        if state!=0x1000 or prot!=0x04 or size<65536 or size>64*1024*1024: continue
        head=rd(base,min(size,4096))
        if not head: continue
        if sum(1 for i in range(0,len(head)-1,2) if 0x81<=head[i]<=0x9f or 0xe0<=head[i]<=0xfc) < 20: continue
        b=rd(base,size)
        if not b: continue
        for m in PAT.finditer(b):
            raw=m.group(0)
            if len(raw)<8: continue
            try: s=raw.decode('cp932')
            except Exception: continue
            if hira(s)<1 or any(0xff61<=ord(c)<=0xff9f for c in s): continue
            if s in seen: continue
            seen.add(s); new+=1
            # 对齐留到离线批量做（此处只采集，保证每轮快）
            P=raw; key=None; off=None
            with open(DB,'a',encoding='utf-8') as f:
                f.write(json.dumps({'off':off,'key':key,'s':s},ensure_ascii=False)+'\n')
    print('轮%d 新增%d 可对齐%d 用时%.1fs 累计%d'%(r+1,new,aligned,time.time()-t0,len(seen)),flush=True)
    if r<ROUNDS-1: time.sleep(SLEEP)
