#!/usr/bin/env python3
"""[PC-JP]Psychic Rain — REAL scenario extractor.

The on-disk system/exec.dat (+ _exec.dat) are a 断罪のマリア LEFTOVER (decoy);
the genuine Psychic Rain scenario is embedded in psychic_rain.exe as the PE
resource type=EXEC / name=EXEC / id=0 (Malie VM script). This carves that
resource and extracts text. Protagonist 沙耶 comes from malie.ini NAME01.
双版对照: multi-box messages -> segment lines + merged line.
"""
import os, struct, sys, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import malie_extract as M

EXE_DEFAULT = r"psychic_rain\psychic_rain.exe"
NAME_DEFAULT = "沙耶"
SKIP_AFTER = {1:4,2:1,3:2,4:1,5:2,6:2}

# ---- PE resource carver (replicates probe_pr_exeres) ----
def carve_exec_resource(exe_path):
    d = open(exe_path,"rb").read()
    e_lfanew = struct.unpack_from("<I",d,0x3c)[0]
    opt = d[e_lfanew+24]
    ns = struct.unpack_from("<H",d,e_lfanew+6)[0]
    soh = struct.unpack_from("<H",d,e_lfanew+20)[0]; sh = e_lfanew+24+soh
    secs=[]
    for i in range(ns):
        b=sh+i*40
        secs.append((d[b:b+8].split(b"\x00")[0],struct.unpack_from("<I",d,b+8)[0],
                     struct.unpack_from("<I",d,b+12)[0],struct.unpack_from("<I",d,b+16)[0],
                     struct.unpack_from("<I",d,b+20)[0]))
    def rva2off(rva):
        for nm,vsize,vrva,rawsize,rawoff in secs:
            if vrva<=rva<vrva+vsize: return rawoff+(rva-vrva)
        return None
    resrva = struct.unpack_from("<I",d,e_lfanew+24+(96 if opt==0x10b else 112))[0]
    base_off = rva2off(resrva)
    def get_name(o):
        p=base_off+o; l=struct.unpack_from("<H",d,p)[0]
        return d[p+2:p+2+l*2].decode("utf-16-le","replace")
    found=[]
    def walk(eo, path):
        ent=base_off+eo
        nc=struct.unpack_from("<H",d,ent+12)[0]; ic=struct.unpack_from("<H",d,ent+14)[0]
        ch=ent+16
        for i in range(nc+ic):
            co=ch+i*8
            nid=struct.unpack_from("<I",d,co)[0]; dto=struct.unpack_from("<I",d,co+4)[0]
            nm=get_name(nid&0x7fffffff) if (nid&0x80000000) else str(nid)
            if dto&0x80000000: walk(dto&0x7fffffff, path+[nm])
            else:
                de=base_off+dto; rva=struct.unpack_from("<I",d,de)[0]; sz=struct.unpack_from("<I",d,de+4)[0]
                found.append((path+[nm], rva2off(rva), sz))
    walk(0,[])
    for pth,off,size in found:
        if pth[:2]==["EXEC","EXEC"] or (len(pth)>=2 and pth[0]=="EXEC" and pth[1]=="EXEC"):
            return d[off:off+size], (pth,off,size)
    raise RuntimeError("EXEC resource not found in %s"%exe_path)

# ---- corrected box decoder (handles every 07 XX control code) ----
def decode_boxes(s, name_default=NAME_DEFAULT):
    out=[]
    for seg in s.split("\x07\x06"):
        o=[]; i=0; n=len(seg)
        while i<n:
            c=ord(seg[i])
            if c==7 and i+1<n:
                sub=ord(seg[i+1]); i+=2
                if sub==12:
                    o.append(name_default)
                    j=seg.find("\x00",i); i=n if j<0 else j+1   # 跳过 <id> 00 参数
                elif sub==1:                      # 注音：本体<0A>読み<00>
                    j=seg.find("\x00",i); j=n if j<0 else j
                    o.append(seg[i:j].split("\x0a")[0]); i=(j+1) if j<n else n
                elif sub in (7,8):                # 语音名 带NUL参数
                    j=seg.find("\x00",i); i=n if j<0 else j+1
                # sub in (4,6,9) 等其它控制码：直接丢弃（i 已前进2）
                continue
            if c==0 or c==0xA: i+=1; continue
            if 1<=c<=6: i+=1+SKIP_AFTER.get(c,0); continue
            o.append(seg[i]); i+=1
        t="".join(o).strip()
        if t: out.append(t)
    return out

def extract_script(data, name_default):
    P=M.parse_exec(data)
    msgs,_=M.walk_script(P, name_default)
    out, dual=[] ,0
    for s in msgs:
        boxes=decode_boxes(s, name_default)
        boxes=[b for b in boxes if b.strip()]
        if len(boxes)>=2:
            dual+=1
            for b in boxes: out.append(b)
            out.append("".join(boxes))
        elif boxes:
            out.append(boxes[0])
    return out, dual

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("exe", nargs="?", default=EXE_DEFAULT, help="psychic_rain.exe (or dir containing it)")
    ap.add_argument("out")
    ap.add_argument("--name", default=NAME_DEFAULT)
    a=ap.parse_args()
    exe=a.exe
    if os.path.isdir(exe):
        exe=os.path.join(exe,"psychic_rain.exe")
    raw,(pth,off,size)=carve_exec_resource(exe)
    sys.stderr.write("# EXEC resource: %s off=%s size=%d\n"%(pth,hex(off),size))
    lines,dual=extract_script(raw, a.name)
    with open(a.out,"wb") as f:
        f.write(b"\xef\xbb\xbf")
        for ln in lines:
            f.write(ln.encode("utf-8")); f.write(b"\n")
    sys.stderr.write("# TOTAL lines=%d dual_msgs=%d\n"%(len(lines),dual))

if __name__=="__main__":
    main()
