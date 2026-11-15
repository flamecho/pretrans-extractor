import ctypes, ctypes.wintypes as w, sys
k=ctypes.WinDLL('kernel32',use_last_error=True)
PID=7140
PROC=0x0410|0x0010  # VM_READ|VM_QUERY
h=k.OpenProcess(PROC,False,PID)
if not h: print('OpenProcess fail',ctypes.get_last_error()); sys.exit(1)
class MBI(ctypes.Structure):
    _fields_=[('BaseAddress',ctypes.c_void_p),('AllocationBase',ctypes.c_void_p),('AllocationProtect',w.DWORD),
              ('RegionSize',ctypes.c_size_t),('State',w.DWORD),('Protect',w.DWORD),('Type',w.DWORD)]
def regions():
    addr=0; mbi=MBI()
    while addr < 0x80000000:
        if not k.VirtualQueryEx(h,ctypes.c_void_p(addr),ctypes.byref(mbi),ctypes.sizeof(mbi)): break
        base=mbi.BaseAddress or 0; size=mbi.RegionSize
        yield base,size,mbi.State,mbi.Protect
        addr=base+size
        if size==0: break
READABLE={0x02,0x04,0x20,0x40,0x80}
def rd(base,size):
    buf=ctypes.create_string_buffer(size)
    got=ctypes.c_size_t(0)
    if k.ReadProcessMemory(h,ctypes.c_void_p(base),buf,size,ctypes.byref(got)):
        return buf.raw[:got.value]
    return None
pats={}
for name,txt in (('泥だんご事件','泥だんご事件'),('原田奈緒','原田奈緒'),('クラスメイト','クラスメイト')):
    pats[name+'_cp932']=txt.encode('cp932')
    pats[name+'_utf16']=txt.encode('utf-16le')
hits={}
tot=0
for base,size,state,prot in regions():
    if state!=0x1000 or prot not in READABLE: continue
    if size>64*1024*1024: size=64*1024*1024
    b=rd(base,size)
    if not b: continue
    tot+=1
    for nm,p in pats.items():
        i=b.find(p)
        while i>=0:
            hits.setdefault(nm,[]).append(base+i)
            i=b.find(p,i+1)
            if len(hits[nm])>50: break
print('可读区数',tot)
for nm,v in hits.items(): print('%-22s %d %s'%(nm,len(v),[hex(x) for x in v[:3]]))
