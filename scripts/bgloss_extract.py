# -*- coding: utf-8 -*-
"""Butterfly Gloss (WillPlus / AdvHD) text extractor.

Disc set:
  DKGDISC1.iso     : base game  -> Rio.arc   (199 WSC scripts)
  DKGAPPEND.iso    : 'After Love' patch -> RIO+.arc (OMK_A02/A03/C02/C03)

Engine : WillPlus / AdvHD  (.wsc bytecode, arc 'ext-group' container)
Cipher : every byte of a WSC file is rotl_8(c, 6)  (decrypt = rotl_8(c, 6))
Text   : op41 = narration line ; op42 = speaker+line ; op02 = choices
Line   : one message box == one line. literal '\\n' (0x5C 0x6E) = soft break -> merged.
"""
import struct, re, sys, os

def rotl8(c, n): return ((c << n) | (c >> (8 - n))) & 0xFF
def decrypt(b): return bytes(rotl8(c, 6) for c in b)

GENERIC = {0x03:7,0x06:5,0x08:2,0x0A:1,0x0C:3,0x22:4,0x26:2,0x45:4,0x47:2,0x49:3,
 0x4F:4,0x51:5,0x52:2,0x74:2,0x82:3,0x83:1,0x84:1,0x8B:1,0xE2:1,0xB8:3,
 0x30:4,0x4E:4,0x62:1,0x85:2,0x86:2,0x88:3,0x89:1,0x8A:1,0x8C:3,0x8E:1,
 0xBC:4,0xBD:2,0xBE:1,0xE5:1,0x4A:6,0x4B:16,0xB1:5,0x68:9,0x65:8,0x67:8,
 0x66:18,0x4C:8,0x63:3,0xB9:3,0x64:8,0xA6:1,0x19:5,0x4D:13,0xD0:9,0x28:5,
 0xFF:8,0xB4:12,0xE4:2,0x76:17,0x01:10,0xA8:16,0x0B:2,0x05:2,0x70:8,0x29:4,
 0xB5:7,0x55:1,0xBB:1,0x2C:12,0x8D:1,0x04:0,0x72:1,0xB3:2,
 0xE6:2,0x0D:7}                                    # + this-game opcodes
STRING = {0x50:0,0x54:0,0x61:1,0x73:9,0xB6:2,0x09:2,0xE0:0,0x41:4,0x43:6,0x46:9,
 0x48:11,0x23:9,0x21:10,0x07:0,0xB2:2,0x25:11,0xBA:11}
DOUBLESTRING = {0x42:5}

def parse_arc(d):
    num = struct.unpack_from("<I", d, 0)[0]
    exts = []; p = 4
    for _ in range(num):
        ext = d[p:p+4].split(b'\x00')[0].decode('cp932','replace')
        cnt, st = struct.unpack_from("<II", d, p+4); p += 12
        exts.append((ext, cnt, st))
    out = {}
    for ext, cnt, st in exts:
        q = st
        for _ in range(cnt):
            name = d[q:q+13].split(b'\x00')[0].decode('cp932','replace')
            ln, so = struct.unpack_from("<II", d, q+13); q += 21
            out[name] = (ext, ln, so)
    return out

def walk(b):
    i = 0; n = len(b)
    while i < n:
        op = b[i]; i += 1
        try:
            if op == 0x02:
                nch = struct.unpack_from("<H", b, i)[0]; i += 2
                ch = []
                for _ in range(nch):
                    i += 2
                    s1 = b[i:b.index(b'\x00', i)]; i += len(s1)+1
                    i += 4
                    s2 = b[i:b.index(b'\x00', i)]; i += len(s2)+1
                    ch.append((s1, s2))
                yield (op, ch)
            elif op in STRING:
                i += STRING[op]
                s = b[i:b.index(b'\x00', i)]; i += len(s)+1
                yield (op, [s])
            elif op in GENERIC:
                i += GENERIC[op]
            elif op in DOUBLESTRING:
                i += DOUBLESTRING[op]
                s1 = b[i:b.index(b'\x00', i)]; i += len(s1)+1
                s2 = b[i:b.index(b'\x00', i)]; i += len(s2)+1
                yield (op, [s1, s2])
            else:
                return
        except Exception:
            return

def clean(t):
    t = re.sub(r'[\x00-\x1f]', '', t)                       # stray control bytes
    t = t.replace('%K%P','').replace('%K','').replace('%P','').replace('%O','')
    t = re.sub(r'(?:\\n)+[ \u3000]*', '', t)                # merge soft line breaks (+indent)
    t = t.strip(' \u3000\t')
    m = re.match(r'^【[^】]*】[ \u3000]*', t)                 # drop speaker tag
    if m:
        t = t[m.end():].strip(' \u3000\t')
    return t

def messages_of(b):
    out = []
    for op, ss in walk(b):
        if op == 0x41:
            t = clean(ss[0].decode('cp932','replace'))
            if t: out.append(t)
        elif op == 0x42:
            t = clean(ss[1].decode('cp932','replace'))
            if t: out.append(t)
        elif op == 0x02:
            for s1, s2 in ss:
                t = clean(s1.decode('cp932','replace'))
                if t: out.append(t)
    return out

def extract_arc(path, order_key):
    d = open(path,'rb').read()
    ents = parse_arc(d)
    names = [n for n in ents if order_key(n) >= 0]
    names.sort(key=lambda n: (order_key(n), n))
    out = []
    for n in names:
        ext, ln, so = ents[n]
        if ext != 'WSC':
            continue
        out += messages_of(decrypt(d[so:so+ln]))
    return out

def write_txt(path, lines):
    with open(path, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(('\n'.join(lines) + '\n').encode('utf-8'))

if __name__ == '__main__':
    base = sys.argv[1]; outdir = sys.argv[2]
    def k(n):
        for i, p in enumerate(("BG_","BGA_","BGC_","OMK_")):
            if n.startswith(p): return i
        return -1
    lines = extract_arc(base, k)
    os.makedirs(outdir, exist_ok=True)
    write_txt(os.path.join(outdir, "Butterfly Gloss_全文本.txt"), lines)
    print("base lines:", len(lines))
