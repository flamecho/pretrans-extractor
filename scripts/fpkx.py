"""FPK 解包（可给外部索引只取指定条目；重名自动加序号，不覆盖）。"""
import struct, sys, os, json
p, outdir = sys.argv[1], sys.argv[2]
idx = json.load(open(sys.argv[3])) if len(sys.argv)>3 else None
f = open(p,'rb')
if idx is None:
    f.seek(0); cnt = struct.unpack('<I', f.read(4))[0]
    f.seek(0x20); idx=[]
    for i in range(cnt):
        b=f.read(32); name=b[:16].split(b'\0')[0].decode('cp932','replace')
        s,o=struct.unpack('<II', b[16:24]); idx.append({"name":name,"size":s,"off":o})
os.makedirs(outdir, exist_ok=True)
seen={}
for e in idx:
    n=e['name']; 
    if n in seen:
        seen[n]+=1; base,ext=os.path.splitext(n); n=f"{base}_{seen[n]}{ext}"
    else: seen[n]=0
    f.seek(e['off']); data=f.read(e['size'])
    open(os.path.join(outdir,n),'wb').write(data)
print("extracted", len(idx), "->", outdir)
