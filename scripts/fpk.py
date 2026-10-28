"""FPK 容器头解析：条目表（名 / 偏移 / 大小）→ 可选导出 JSON，附扩展名直方图。"""
import struct, sys, os, json
p = sys.argv[1]
d = open(p,'rb').read(0x40000)
cnt = struct.unpack_from('<I', d, 0)[0]
total = struct.unpack_from('<Q', d, 8)[0]
hdr  = struct.unpack_from('<I', d, 0x10)[0]
dstart = struct.unpack_from('<I', d, 0x14)[0]
print(f"count={cnt} totalsize={total} hdrField={hdr:#x} dataStart={dstart:#x}")
ents=[]
off=0x20
for i in range(cnt):
    name = d[off:off+16].split(b'\0')[0].decode('cp932','replace')
    size, o = struct.unpack_from('<II', d, off+16)
    ents.append((name,size,o))
    off += 32
print("entryEnd=", hex(off))
print("first 5:", ents[:5])
print("last 3:", ents[-3:])
s=sum(e[1] for e in ents)
print("sum sizes:", s, hex(s), "expected", hex(total))
from collections import Counter
print(Counter(e[0].rsplit('.',1)[-1].upper() for e in ents))
if len(sys.argv)>2: json.dump([{"name":n,"size":s2,"off":o} for n,s2,o in ents], open(sys.argv[2],'w'))
