#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""5pb PSP (Musketeer/EVB engine) MARC font atlas unpacker.
Usage: python marc_font.py ar999_0000.bin out_dir
- parses MARC (magic + u32 count + count x (off,end) interleaved table)
- e0 = font atlas: 64B palette (16-color white w/ alpha ramp) + 8bpp swizzled pixels
- unswizzle: block 32x8 (256B), W=512: off=(y//8)*(W//32)*256+(x//32)*256+(y%8)*32+(x%32)
- e1 = SJIS string table (cp932 readable)
Outputs: atlas.png (clean glyph sheet), strings.txt
"""
import sys, os, struct
from PIL import Image

def parse_marc(d):
    assert d[:4]==b'MARC', 'not MARC'
    cnt=struct.unpack_from('<I',d,4)[0]
    entries=[]; o=8
    for i in range(cnt):
        off=struct.unpack_from('<I',d,o)[0]; end=struct.unpack_from('<I',d,o+4)[0]
        entries.append((off,end)); o+=8
    return entries

def unswizzle(px,W,H,bw=32,bh=8):
    out=bytearray(W*H); rowblocks=W//bw; bb=bw*bh
    for y in range(H):
        for x in range(W):
            blk=(y//bh)*rowblocks+(x//bw)
            off=blk*bb+(y%bh)*bw+(x%bw)
            if off<len(px): out[y*W+x]=px[off]
    return out

def main():
    src, outdir = sys.argv[1], sys.argv[2]
    d=open(src,'rb').read()
    os.makedirs(outdir,exist_ok=True)
    entries=parse_marc(d)
    print('MARC entries:', [(hex(a),hex(b)) for a,b in entries[:6]], '...' if len(entries)>6 else '')
    off,end=entries[0]
    e0=d[off:end]
    pal=e0[:64]
    px=e0[64:64+512*872]
    lin=unswizzle(px,512,872)
    # apply palette (index*17 gray)
    arr=bytes(min(255,(v*17 if v<16 else 0)) for v in lin)
    Image.frombytes('L',(512,872),arr).save(os.path.join(outdir,'atlas.png'))
    print('atlas.png written (512x872)')
    off2,end2=entries[1]
    e1=d[off2:end2]
    if e1[:4]==b'MARC':
        subs=parse_marc(e1)
        lines=[]
        for i,(so,se) in enumerate(subs):
            blob=e1[so:se].split(b'\x00')[0]
            try: lines.append(blob.decode('cp932'))
            except: lines.append(repr(blob))
        open(os.path.join(outdir,'strings.txt'),'w',encoding='utf-8').write('\n'.join(lines))
        print('strings.txt written (%d entries)'%len(lines))

if __name__=='__main__':
    main()
