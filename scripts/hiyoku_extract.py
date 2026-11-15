# -*- coding: utf-8 -*-
"""[JP]比翼は愛薊の彼方へ ～久遠の想～ (PC / SandalDash) text extractor.

Container  script.dat = ARCG-like "RK1" archive
    data region : entry blobs back to back from offset 0
    dir table   : 32 B / entry -> [char name[12]][u32 0][u32 compSize][u32 rawSize]
                                  [u32 flag][u32 offset]
    tail        : [u32 ?]['RK1\0'][u32 count][u32 table_off]
    each entry blob is LZSS-compressed.

LZSS (verified 79/79 exact rawSize):
    flag byte, LSB first, bit=1 -> literal, bit=0 -> match
    match = 2 bytes: pos = b1 | ((b2 & 0xF0) << 4)   (12 bit)
                     len = (b2 & 0x0F) + 3           (3..18)
    ring 4096, initialised with 0x00, r starts at 4096-18.

Decompressed entry = N x 144-byte records:
    [u8 code][text: 64 B, cp932 + NUL][field2: 64 B][tail: 15 B]

Codes (L0):
    0x6a  speaker name (independent name window) / label string
    0x64  one display row of the current box
    0x6e  end of box   (wait for click)
    0x6f  advance/clear
    0xcd  choice item -> option text lives in FIELD2 ('『…』')
    0xce  end of choice group
    0xc8/0xa5/0xaa/0xa0  branch & jump
    0xd2  jump to another scene file ('0100' etc.)
    0x78/0x7a/0x7c/0x7e/0x82/0x83/0x96/0x97/0x9c/0x9b  graphics / flags

Line rule (L0): one click == one box == 0x6a(name) + 1..3 x 0x64(rows) + 0x6e + 0x6f
    verified: every 0x64 follows 0x6a or 0x64 (0 exceptions);
              every group ends with (0x6e, 0x6f).
Half-width (...) in a text field is ruby markup -> strip the parens, drop the
kana field (rendered as furigana above the base text).
"""
import struct, os, sys, re, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SRC = os.path.join(VNTRANS_HOME, '_work_hiryou/[JP]比翼は愛薊の彼方へ ～久遠の想～/SetUp/script.dat')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[JP]比翼は愛薊の彼方へ ～久遠の想～.txt')

REC = 144
F1 = slice(1, 0x41)
F2 = slice(0x41, 0x81)

d = open(SRC, 'rb').read()

# ---------------- container ----------------
def load_entries():
    tail = d.rfind(b'RK1\x00')
    if tail < 0:
        raise SystemExit('RK1 marker not found')
    count = struct.unpack_from('<I', d, tail + 4)[0]
    table = struct.unpack_from('<I', d, tail + 8)[0]
    p = table
    out = []
    for _ in range(count):
        name = d[p:p+12].split(b'\x00')[0].decode('ascii')
        z, cs, rs, fl, off = struct.unpack_from('<IIIII', d, p+12)
        out.append((name, cs, rs, fl, off))
        p += 32
    return out

def lzss(data, win=4096, minlen=3, maxlen=18, init=0x00):
    out = bytearray()
    ring = bytearray([init]) * win
    r = win - maxlen
    p = 0
    n = len(data)
    while p < n:
        flags = data[p]; p += 1
        for i in range(8):
            if p >= n:
                break
            if (flags >> i) & 1:
                c = data[p]; p += 1
                out.append(c); ring[r] = c; r = (r + 1) % win
            else:
                if p + 1 >= n:
                    break
                b1, b2 = data[p], data[p+1]; p += 2
                pos = b1 | ((b2 & 0xF0) << 4)
                ln = (b2 & 0x0F) + minlen
                for k in range(ln):
                    c = ring[(pos + k) % win]
                    out.append(c); ring[r] = c; r = (r + 1) % win
    return bytes(out)

# ---------------- decode helpers ----------------
RUBY = re.compile(r'\(([^()]*)\)')

def cp(b):
    try:
        return b.decode('cp932')
    except UnicodeDecodeError:
        return None

def strip_ruby(t):
    """(郭隗)が… -> 郭隗が…   (half-width parens are ruby markup, not text)"""
    return RUBY.sub(r'\1', t)

def records(blob):
    for k in range(0, len(blob) // REC):
        yield blob[k*REC:(k+1)*REC]

# ---------------- scene order ----------------
def scene_order(entries):
    names = [e[0] for e in entries]
    have = set(names)
    seen = set()
    order = []

    def walk(name):
        if name in seen or name not in have:
            return
        seen.add(name)
        order.append(name)
        cs, rs, fl, off = [e for e in entries if e[0] == name][0][1:]
        blob = lzss(d[off:off+cs])
        for r in records(blob):
            if r[0] == 0xd2:
                tgt = r[F1].split(b'\x00')[0].decode('ascii', 'replace').strip()
                if tgt:
                    walk(tgt)

    walk('START.BIN')
    for n in names:
        walk(n)
    return order

# ---------------- extraction ----------------
def main():
    entries = load_entries()
    byname = {e[0]: e for e in entries}
    order = scene_order(entries)

    lines = []
    stat = collections.Counter()
    for name in order:
        cs, rs, fl, off = byname[name][1:]
        blob = lzss(d[off:off+cs])
        if len(blob) % REC:
            stat['bad_len'] += 1
            continue
        recs = list(records(blob))
        i = 0
        n = len(recs)
        while i < n:
            code = recs[i][0]
            if code == 0xcd:
                # choice group: consecutive 0xcd
                while i < n and recs[i][0] == 0xcd:
                    opt = cp(recs[i][F2].split(b'\x00')[0])
                    if opt:
                        lines.append(opt.strip())
                        stat['choice'] += 1
                    i += 1
                continue
            if code == 0x6a:
                j = i + 1
                rows = []
                while j < n and recs[j][0] == 0x64:
                    t = cp(recs[j][F1].split(b'\x00')[0])
                    if t:
                        rows.append(strip_ruby(t))
                    j += 1
                if rows and j < n and recs[j][0] == 0x6e:
                    s = ''.join(rows).strip(' \u3000')
                    if s:
                        lines.append(s)
                        stat['line'] += 1
                    i = j + 1
                    continue
            i += 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(('\n'.join(lines) + '\n').encode('utf-8'))
    print('scenes:', len(order))
    print('lines:', stat['line'], 'choices:', stat['choice'], 'total:', len(lines))
    print('bad_len scenes:', stat['bad_len'])
    print('bytes:', os.path.getsize(OUT))
    for t in lines[:4]:
        print('  |', t[:50])
    print('  ...')
    for t in lines[-4:]:
        print('  |', t[:50])

if __name__ == '__main__':
    main()
