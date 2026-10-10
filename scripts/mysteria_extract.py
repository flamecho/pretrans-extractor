#!/usr/bin/env python3
"""英国探偵ミステリア The Crown (PSV, Malie System / MalieVita) exec.dat -> text.

架构同 PC 版 Malie（OmegaVampire 实证），差异：
  - 函数名 / 标签名 = 窄字节(ASCII)，非 UTF-16
  - 字符串表 STRT = **CP932**（非 UTF-16LE）
  - `_ms_message`(vCall id 45) 栈顶参数 = 字符串表下标
"""
import struct, sys, re

def parse_exec(d):
    N = len(d)
    o = 0
    def u32():
        nonlocal o
        v = struct.unpack_from('<I', d, o)[0]; o += 4; return v
    def getnext():
        nonlocal o
        f = u32()
        while f:
            o += 4; f = u32()
    varc = u32()
    for _ in range(varc):
        sz = u32(); o += (sz & 0x7FFFFFFF); getnext(); o += 16
    o += 4
    fcnt = u32(); FUNCS = []
    for _ in range(fcnt):
        sz = u32(); nm = d[o:o+(sz & 0x7FFFFFFF)].rstrip(b'\x00').decode('latin1'); o += (sz & 0x7FFFFFFF)
        fid = u32(); res = u32(); coff = u32(); FUNCS.append((nm, fid, coff))
    lcnt = u32()
    for _ in range(lcnt):
        sz = u32(); o += (sz & 0x7FFFFFFF) + 4
    dsz = u32(); VM_DATA = d[o:o+dsz]; o += dsz
    csz = u32(); VM_CODE = d[o:o+csz]; o += csz
    unk = u32()
    cnt = unk
    vIdx = [struct.unpack_from('<II', d, o+i*8) for i in range(cnt)]; o += cnt*8
    stsz = u32(); STRT = d[o:o+stsz]
    return {"FUNCS": FUNCS, "VM_DATA": VM_DATA, "VM_CODE": VM_CODE, "vIdx": vIdx, "STRT": STRT}

SKIP_AFTER = {1: 4, 2: 1, 3: 2, 4: 1, 5: 2, 6: 2}

def walk_script(P, name_default="マリア"):
    FUNCS, VM_DATA, VM_CODE, vIdx, STRT = P["FUNCS"], P["VM_DATA"], P["VM_CODE"], P["vIdx"], P["STRT"]
    NAME2ID = {n: i for n, i, c in FUNCS}
    NAME2OFF = {n: c for n, i, c in FUNCS}
    def gs(i):
        off, ln = vIdx[i]; return STRT[off:off+ln].decode('cp932', 'replace')
    MSG = NAME2ID.get("_ms_message")
    NM = NAME2ID.get("MALIE_NAME")
    TAG = NAME2ID.get("tag")
    ST = []; pc = NAME2OFF["maliescenario"]; out = []
    n_msg = 0
    while pc < len(VM_CODE):
        op = VM_CODE[pc]
        if op == 0x33: break
        i = pc+1; sz = 1; par = None; push = None
        if op <= 2: par = struct.unpack_from("<I", VM_CODE, i)[0]; sz = 5
        elif op == 3: par = struct.unpack_from("<I", VM_CODE, i)[0]; sz = 6
        elif op == 4: par = VM_CODE[i]; sz = 3
        elif op == 7:
            if ST: ST.pop()
        elif op in (8, 0xD): par = struct.unpack_from("<I", VM_CODE, i)[0]; sz = 5; push = par | 0x80000000
        elif op == 9: par = VM_CODE[i]; sz = 2; push = par
        elif op == 0xA: par = struct.unpack_from("<H", VM_CODE, i)[0]; sz = 3; push = par
        elif op == 0xC: par = struct.unpack_from("<I", VM_CODE, i)[0]; sz = 5; push = par
        elif op == 0xE:
            if ST: ST.pop()
        elif op == 0xF: push = 0x80000000
        elif op == 0x11: par = VM_CODE[i]; sz = 2; push = par | 0x80000000
        elif op in (0x14,0x15,0x16,0x17,0x18,0x19,0x1A,0x1B,0x1E,0x1F,0x21,0x22,0x23,0x24,0x25,0x26,0x28):
            if ST: ST.pop()
        elif op == 0x2D: par = struct.unpack_from("<I", VM_CODE, i)[0]; sz = 5; push = 0x80000000
        elif op == 0x31: par = struct.unpack_from("<I", VM_CODE, i)[0]; sz = 5
        elif op == 0x32: par = VM_CODE[i]; sz = 2
        if push is not None: ST.append(push)
        if op in (0x2D, 4, 3):
            if par == MSG:
                if ST: ST.pop()
                idx = (ST[-1] if ST else 0) & 0x7FFFFFFF
                ST.clear(); ST.append(0)
                out.append((idx, gs(idx)))
                n_msg += 1
            elif par == NM or par == TAG:
                pass
        pc += sz
    sys.stderr.write("walked to pc=0x%x, msgs=%d\n" % (pc, n_msg))
    return out, gs

def decode_boxes(s, name_default="マリア"):
    out = []
    for seg in s.split("\x07\x06"):
        o = []; i = 0; n = len(seg)
        while i < n:
            c = ord(seg[i])
            if c == 7 and i+1 < n:
                sub = ord(seg[i+1]); i += 2
                if sub == 12:
                    o.append(name_default)
                elif sub == 1:
                    j = seg.find("\x00", i); j = n if j < 0 else j
                    o.append(seg[i:j].split("\x0a")[0]); i = j+1 if j < n else n
                elif sub in (7, 8):
                    j = seg.find("\x00", i); i = n if j < 0 else j+1
                continue
            if c == 0 or c == 0xA: i += 1; continue
            if 1 <= c <= 6: i += 1 + SKIP_AFTER.get(c, 0); continue
            o.append(seg[i]); i += 1
        t = "".join(o).strip()
        if t: out.append(t)
    return out

if __name__ == "__main__":
    d = open(sys.argv[1], "rb").read()
    P = parse_exec(d)
    msgs, gs = walk_script(P)
    for idx, s in msgs:
        print("### idx=%d" % idx)
        print(repr(s))
