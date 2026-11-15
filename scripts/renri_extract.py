# -*- coding: utf-8 -*-
"""[JP]比翼は愛薊の彼方へ ～連理の夢～ (PC 2008 / SandalDash) text extractor.

Same engine family as ～久遠の想～ (see engines/sandaldash-rk1.md), with a few
per-title differences listed below.

Container  script.dat = "RK1" archive
    data region : entry blobs back to back from offset 0
    dir table   : 32 B / entry -> [char name[12]][u32 0][u32 compSize][u32 rawSize]
                                  [u32 flag][u32 offset]
    tail        : [u32 ?]['RK1\0'][u32 count][u32 table_off]
    closure     : sum(compSize) == table_off      (here 1,373,630 == 0x14F5BE)

LZSS  flag byte, LSB first, bit=1 -> literal, bit=0 -> match
      match = 2 bytes: pos = b1 | ((b2 & 0xF0) << 4)   (12 bit)
                       len = (b2 & 0x0F) + 3           (3..18)
      ring 4096, **init 0x00**, r starts at 4096-18.
      !! init 0x20 also satisfies rawSize but fills holes with spaces:
         f1 "text" count jumps 24,572 -> 58,785 while the Japanese ratio drops
         66.6% -> 27.8% and 0x20 shows up as a bogus record code. Length alone
         is NOT a valid acceptance test.

Decompressed entry = N x 144-byte records:
    [u8 code][f1: 64 B, cp932 + NUL][f2: 64 B][tail: 15 B]
    tail[1] of a 0x64 record == row index inside the box (0,1,2)
        measured: 1-row boxes (0,) x5815 | 2-row (0,1) x2966 | 3-row (0,1,2) x75
        -> independent structural proof that a group == one text box.

Codes (L0):
    0x6a  speaker name window (independent) / label  -> NAME NOT IN TEXT
    0x64  one display row of the current box          -> COLLECT (f1)
    0x6e  end of box (wait for click)
    0x6f  advance / clear
    0x69  author block heading (chapter title)        -> NOT SHOWN, DO NOT COLLECT
          evidence: only 2 of 56 appear before a picture op; 37 go straight into
          0xdc/0xdd (open box). Per layout-cases.md the real title card is
          displayed in the flow -- this one is a block label.
    0xcd  choice item -> FIELD2 is the option text    -> COLLECT (f2)
          (this title has NO '『…』' wrapper around the option text)
    0xce  end of choice group
    0xc8/0xa5/0xaa/0xa0  branch & jump
    0xd2  jump to another scene file
    0xdc / 0xdd  open box (scene start)
    0x78/0x7a/0x7e/0x82/0x83/0x96/0x97/0x9b/0x9c/0x9d graphics / SE / flags
    0x84/0x8c/0x8d/0x9e/0xfc ...  playback / misc

Line rule (L0): one click == one box == 0x6a + 1..3 x 0x64 + (0x6e,0x6f)
    every 0x64 follows 0x6a or 0x64 (11,972 hits, 0 exceptions)
    8,855 of 8,856 groups end with (0x6e,0x6f); the 1 exception (OMAKE.BIN
    rec 720) goes straight into a scene change -> box still valid, no click wait.
Half-width (...) in f1 is ruby markup (base text kept, parens dropped);
the kana lives in f2 and is discarded. Full-width （） is a real parenthesis.
"""
import struct, os, re, collections, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

# Author block headings (0x69). Structural evidence says they are NOT rendered
# (tail all zero, 37/56 followed straight by an open-box, only 2/56 satisfy the
# "title card" rule in engines/stcm2l.md), so they are excluded by default.
# Pass --with-headings to emit them anyway (prepended in place).
WITH_HEADING = '--with-headings' in sys.argv

SRC = os.path.join(VNTRANS_HOME, '_work_renri/[JP]比翼は愛薊の彼方へ ～連理の夢～/比翼は愛薊の彼方へ～連理の夢～/SetUp/script.dat')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[JP]比翼は愛薊の彼方へ ～連理の夢～.txt')

REC = 144
F1 = slice(1, 0x41)
F2 = slice(0x41, 0x81)

COLLECT_CHOICE = 0xcd
NAME_OP = 0x6a
ROW_OP = 0x64

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
        name = d[p:p+12].split(b'\x00')[0].decode('ascii', 'replace')
        z, cs, rs, fl, off = struct.unpack_from('<IIIII', d, p + 12)
        out.append((name, cs, rs, fl, off))
        p += 32
    if sum(e[1] for e in out) != table:
        raise SystemExit('container closure FAILED: sum(compSize) != table_off')
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
    return RUBY.sub(r'\1', t)

def records(blob):
    for k in range(0, len(blob) - REC + 1, REC):
        yield blob[k:k+REC]

# ---------------- scene order ----------------
def scene_order(entries, blobs):
    names = [e[0] for e in entries]
    have = set(names)
    # 0xd2 operands omit the extension AND mix case ('2800aE' -> '2800AE.BIN'),
    # so the lookup must be case-insensitive with a .BIN fallback.
    up = {n.upper(): n for n in names}
    seen = set()
    order = []

    def norm(t):
        t = t.strip()
        if not t:
            return None
        if t.upper() in up:
            return up[t.upper()]
        if (t + '.BIN').upper() in up:
            return up[(t + '.BIN').upper()]
        return None

    def walk(name):
        if name in seen or name not in have:
            return
        seen.add(name)
        order.append(name)
        for r in records(blobs[name]):
            if r[0] == 0xd2:
                tgt = r[F1].split(b'\x00')[0].decode('ascii', 'replace')
                tgt = norm(tgt)
                if tgt:
                    walk(tgt)

    walk('START.BIN')
    for n in names:
        walk(n)
    return order

# ---------------- extraction ----------------
def main():
    entries = load_entries()
    blobs = {}
    for name, cs, rs, fl, off in entries:
        blob = lzss(d[off:off+cs])
        if len(blob) != rs:
            raise SystemExit('decompress size mismatch on %s: %d != %d' % (name, len(blob), rs))
        blobs[name] = blob

    order = scene_order(entries, blobs)

    lines = []
    stat = collections.Counter()
    for name in order:
        recs = list(records(blobs[name]))
        n = len(recs)
        i = 0
        while i < n:
            code = recs[i][0]
            if code == COLLECT_CHOICE:
                while i < n and recs[i][0] == COLLECT_CHOICE:
                    opt = cp(recs[i][F2].split(b'\x00')[0])
                    if opt:
                        s = opt.strip(' \u3000')
                        if s:
                            lines.append(s)
                            stat['choice'] += 1
                    i += 1
                continue
            if code == NAME_OP:
                j = i + 1
                rows = []
                while j < n and recs[j][0] == ROW_OP:
                    t = cp(recs[j][F1].split(b'\x00')[0])
                    if t:
                        rows.append(strip_ruby(t))
                    j += 1
                if rows:
                    s = ''.join(rows).strip(' \u3000')
                    if s:
                        lines.append(s)
                        stat['line'] += 1
                    i = j
                    continue
                i += 1
                continue
            if WITH_HEADING and code == 0x69:
                t = cp(recs[i][F1].split(b'\x00')[0])
                if t:
                    s = t.strip(' \u3000')
                    if s:
                        lines.append(s)
                        stat['heading'] += 1
                i += 1
                continue
            i += 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(('\n'.join(lines) + '\n').encode('utf-8'))
    print('scenes:', len(order), '/', len(entries))
    print('lines: %d  choices: %d  total: %d' % (stat['line'], stat['choice'], len(lines)))
    print('bytes:', os.path.getsize(OUT))
    for t in lines[:4]:
        print('  |', t[:56])
    print('  ...')
    for t in lines[-4:]:
        print('  |', t[:56])

if __name__ == '__main__':
    main()
