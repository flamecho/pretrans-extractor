# -*- coding: utf-8 -*-
"""SiglusEngine (罪ナル螺旋ノ檻 / Tsuminaru) Scene.pck text extractor.

Pipeline
  1. Scene.pck index (plaintext)  -> per-scene encrypted LZSS blobs
  2. blob XOR SCENE_KEY(256)      -> masked
  3. masked XOR EXE_KEY(16)       -> [u32 arc_size][u32 org_size][LZSS]
  4. LZSS decompress              -> .ss scene chunk (33 x i32 header)
  5. string table at str_list_ofs, each string XOR (28807 * index) % 65536 (u16)
  6. walk op stream; a string push  PUSH(0x02) FM_STR(20) str_id(i32)
     is classified by the op byte that follows:
        0x31 TEXT   -> text-box segment, operand = read-flag index
        0x32 NAME   -> speaker name for the following box
        0x22 OPERATE_2 with operator 0x01 (concat) -> choice-button label
        other       -> resource / internal argument (dropped)
     read_flag_list[flag] = source line no; TEXT ops sharing a line belong to the
     same box (needed for ruby: reading is a concat arg, base kanji is the TEXT).

Usage:
    python siglus_scene_extract.py <GameData dir> [out.txt]
GameData dir must contain Scene.pck (Gameexe.dat optional).
"""
import struct, os, sys, re, glob

# --- per-game 16-byte EXE key (this game) -------------------------------------
EXE_KEY = [0x42, 0x2A, 0xBC, 0x1E, 0x47, 0xDB, 0x68, 0xC8,
           0x91, 0x74, 0xC2, 0x5B, 0xD6, 0x47, 0x99, 0x11]

SCENE_KEY = bytes([
0x70,0xF8,0xA6,0xB0,0xA1,0xA5,0x28,0x4F,0xB5,0x2F,0x48,0xFA,0xE1,0xE9,0x4B,0xDE,
0xB7,0x4F,0x62,0x95,0x8B,0xE0,0x03,0x80,0xE7,0xCF,0x0F,0x6B,0x92,0x01,0xEB,0xF8,
0xA2,0x88,0xCE,0x63,0x04,0x38,0xD2,0x6D,0x8C,0xD2,0x88,0x76,0xA7,0x92,0x71,0x8F,
0x4E,0xB6,0x8D,0x01,0x79,0x88,0x83,0x0A,0xF9,0xE9,0x2C,0xDB,0x67,0xDB,0x91,0x14,
0xD5,0x9A,0x4E,0x79,0x17,0x23,0x08,0x96,0x0E,0x1D,0x15,0xF9,0xA5,0xA0,0x6F,0x58,
0x17,0xC8,0xA9,0x46,0xDA,0x22,0xFF,0xFD,0x87,0x12,0x42,0xFB,0xA9,0xB8,0x67,0x6C,
0x91,0x67,0x64,0xF9,0xD1,0x1E,0xE4,0x50,0x64,0x6F,0xF2,0x0B,0xDE,0x40,0xE7,0x47,
0xF1,0x03,0xCC,0x2A,0xAD,0x7F,0x34,0x21,0xA0,0x64,0x26,0x98,0x6C,0xED,0x69,0xF4,
0xB5,0x23,0x08,0x6E,0x7D,0x92,0xF6,0xEB,0x93,0xF0,0x7A,0x89,0x5E,0xF9,0xF8,0x7A,
0xAF,0xE8,0xA9,0x48,0xC2,0xAC,0x11,0x6B,0x2B,0x33,0xA7,0x40,0x0D,0xDC,0x7D,0xA7,
0x5B,0xCF,0xC8,0x31,0xD1,0x77,0x52,0x8D,0x82,0xAC,0x41,0xB8,0x73,0xA5,0x4F,0x26,
0x7C,0x0F,0x39,0xDA,0x5B,0x37,0x4A,0xDE,0xA4,0x49,0x0B,0x7C,0x17,0xA3,0x43,0xAE,
0x77,0x06,0x64,0x73,0xC0,0x43,0xA3,0x18,0x5A,0x0F,0x9F,0x02,0x4C,0x7E,0x8B,0x01,
0x9F,0x2D,0xAE,0x72,0x54,0x13,0xFF,0x96,0xAE,0x0B,0x34,0x58,0xCF,0xE3,0x00,0x78,
0xBE,0xE3,0xF5,0x61,0xE4,0x87,0x7C,0xFC,0x80,0xAF,0xC4,0x8D,0x46,0x3A,0x5D,0xD0,
0x36,0xBC,0xE5,0x60,0x77,0x68,0x08,0x4F,0xBB,0xAB,0xE2,0x78,0x07,0xE8,0x73,0xBF])

SSHDR = 132
PUSH, TEXT, NAME, OPERATE2 = 0x02, 0x31, 0x32, 0x22

def xor_cycle(buf, key):
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(buf))

def lzss_decompress(src, out_size):
    out = bytearray(); i = 0; n = len(src)
    while len(out) < out_size and i < n:
        ctl = src[i]; i += 1; s = 8
        while s > 0 and len(out) < out_size:
            if ctl & 1:
                if i >= n: break
                out.append(src[i]); i += 1
            else:
                if i + 1 >= n: break
                v = src[i] | (src[i+1] << 8); i += 2
                for _ in range((v & 0x0F) + 2):
                    out.append(out[len(out) - (v >> 4)])
            s -= 1; ctl >>= 1
    return bytes(out)

def load_scene_blobs(pck_path):
    d = open(pck_path, 'rb').read()
    assert struct.unpack('I', d[0:4])[0] == 92, 'not a SiglusEngine Scene.pck'
    P = lambda i: struct.unpack('2I', d[4+i*8:12+i*8])
    sni_o, sni_c = P(6); sn_o, _ = P(7); si_o, si_c = P(8); sd_o, _ = P(9)
    names = []
    for k in range(sni_c):
        no, nl = struct.unpack('2I', d[sni_o+k*8:sni_o+k*8+8])
        names.append((no, nl))
    p = sn_o; nlist = []
    for no, nl in names:
        nlist.append(d[p:p+nl*2].decode('utf-16-le')); p += nl*2
    infos = [struct.unpack('2I', d[si_o+k*8:si_o+k*8+8]) for k in range(si_c)]
    blobs = []
    for k, (off, size) in enumerate(infos):
        raw = d[sd_o+off:sd_o+off+size]
        masked = xor_cycle(raw, SCENE_KEY)
        plain = xor_cycle(masked, EXE_KEY)
        arc, org = struct.unpack('2I', plain[:8])
        blobs.append((nlist[k], lzss_decompress(plain[8:], org)))
    return blobs

class Scene:
    def __init__(self, name, chunk):
        self.name = name; self.d = chunk
        h = struct.unpack('33I', chunk[:SSHDR]); self.h = h
        self.scn_ofs, self.scn_size = h[1], h[2]
        self.stridx_ofs, self.stridx_cnt = h[3], h[4]
        self.strdat_ofs, self.str_cnt = h[5], h[6]
        self.rf_ofs, self.rf_cnt = h[31], h[32]
        self.words = [self._word(i) for i in range(self.str_cnt)]
        self.rf = (list(struct.unpack('<%di' % self.rf_cnt,
                    chunk[self.rf_ofs:self.rf_ofs+self.rf_cnt*4]))
                   if self.rf_cnt and self.rf_ofs+self.rf_cnt*4 <= len(chunk) else [])

    def _word(self, i):
        off, ln = struct.unpack('2I', self.d[self.stridx_ofs+i*8:self.stridx_ofs+i*8+8])
        raw = self.d[self.strdat_ofs+off*2:self.strdat_ofs+off*2+ln*2]
        lk = (28807 * i) % 65536
        out = bytearray()
        for j in range(ln):
            out += struct.pack('<H', struct.unpack('<H', raw[j*2:j*2+2])[0] ^ lk)
        return out.decode('utf-16-le', 'replace')

    def boxes(self):
        d = self.d; st = self.scn_ofs; en = min(st+self.scn_size, len(d))
        items = []; cur = None; p = st
        while p < en - 9:
            if d[p] == PUSH and d[p+1:p+5] == b'\x14\x00\x00\x00':
                i = struct.unpack('<i', d[p+5:p+9])[0]
                if 0 <= i < self.str_cnt:
                    nxt = d[p+9]
                    if nxt == NAME:
                        cur = self.words[i]; p += 9; continue
                    if nxt == TEXT:
                        fl = struct.unpack('<i', d[p+10:p+14])[0] if p+14 <= en else -1
                        line = self.rf[fl] if 0 <= fl < len(self.rf) else None
                        txt = self.words[i]
                        if (items and items[-1]['kind'] == 'text'
                                and line is not None and items[-1].get('line') == line):
                            items[-1]['text'] += txt
                        else:
                            items.append({'kind': 'text', 'text': txt,
                                          'line': line, 'name': cur})
                        p += 14; continue
                    if (nxt == OPERATE2 and p+19 <= en and d[p+18] == 0x01
                            and self.words[i]):
                        items.append({'kind': 'choice', 'text': self.words[i],
                                      'name': cur})
                        p += 9; continue
                    p += 9; continue
            p += 1
        return items

def scene_sort_key(name):
    m = re.match(r'scene(\d+)$', name)
    return (0, int(m.group(1))) if m else (1, name)

def main():
    gd = sys.argv[1] if len(sys.argv) > 1 else '.'
    out = sys.argv[2] if len(sys.argv) > 2 else 'scene_text.txt'
    blobs = load_scene_blobs(os.path.join(gd, 'Scene.pck'))
    scenes = [Scene(n, c) for n, c in blobs]
    story = sorted([s for s in scenes if not s.name.startswith('_')],
                   key=lambda s: scene_sort_key(s.name))
    lines = []
    for s in story:
        for it in s.boxes():
            if it['text']:
                lines.append(it['text'])
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('%d scenes -> %d lines -> %s' % (len(story), len(lines), out))

if __name__ == '__main__':
    main()
