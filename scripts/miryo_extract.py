# -*- coding: utf-8 -*-
"""[JP]比翼は愛薊の彼方へ ～未了の因～ (PC 2006 / SandalDash) text extractor.

Third title of the same engine family (see engines/sandaldash-rk1.md §11).
Container / LZSS / 144 B record layout are identical to the other two; the
differences that matter are listed below.

Container  script.dat = "RK1" archive
    tail  : [u32 ?]['RK1\0'][u32 count=74][u32 table_off=0x0E13DF]
    entry : 32 B -> [char name[12]][u32 0][u32 compSize][u32 rawSize][u32 flag][u32 offset]
    closure: sum(compSize) == table_off   (922,591 == 0x0E13DF)

LZSS  flag byte LSB first, bit=1 literal, bit=0 match
      pos = b1 | ((b2 & 0xF0) << 4) ; len = (b2 & 0x0F) + 3 ; ring 4096, init 0x00
      !! init 0x20 again gives 74/74 correct lengths but 36,428 bogus "texts"
         (JP ratio 68.2% -> 39.4%) and a fake 0x20 record code.

Record = 144 B: [u8 code][f1 64 B][f2 64 B][tail 15 B] ; 37,329 records.

Codes (this title):
    0x64  one display row                          -> COLLECT (f1)
    0x6a  speaker name window (OPTIONAL lead-in)   -> NOT in text
    0x6e 0x6f  box end / advance (wait for click)
    0xcd  choice item, text in FIELD2 ('「…」')    -> COLLECT (f2)
    0xce  end of choice group
    0xc8  choice dispatch (f1 = label)
    0xd2  jump to scene (f1 = scene name, no extension)
    0x78/0x7a/0x7e/0x9c  background / sprite / effect / sprite-id
    0x9b/0x9d/0xa5       2-digit ids / scene ref  (not readable text)
    0x74/0x76/0x77/0x82/0x83/0x87/0x8c/0x96/0x97/0x9e/0xaa  playback / flags

BOX RULE (L0) -- ★ this title differs from the previous two:
    a box = consecutive 0x64 rows terminated by (0x6e,0x6f).
    0x6a (name window) is OPTIONAL: 5,893 boxes start with 0x6a, but 19 start
    after 0x6f, 2 after 0x9b, 1 after 0x87 (地の文 boxes with no name window).
    => the previous title's "every 0x64 follows 0x6a/0x64" test does NOT hold
       here (22 exceptions); the anchor must be the (0x6e,0x6f) terminator.
    verified: all 10,163 0x64 records are covered, orphan 0;
              rows per box 1x2757 / 2x2068 / 3x1090  (2757+2*2068+3*1090 = 10,163)
              50 (0x6e,0x6f) pairs have no rows before them (empty boxes).
Half-width (...) in f1 is ruby markup: 25 markers == 25 f2 kana fields.
Full-width （） (202) is a real parenthesis -> keep.
"""
import struct, os, re, collections, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SRC = os.path.join(VNTRANS_HOME, '_work_miryo/[JP]比翼は愛薊の彼方へ ～未了の因～/比翼は愛薊の彼方へ/SetUp/script.dat')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[JP]比翼は愛薊の彼方へ ～未了の因～.txt')

REC = 144
F1 = slice(1, 0x41)
F2 = slice(0x41, 0x81)

NAME_OP = 0x6a
ROW_OP = 0x64
END_OPS = (0x6e, 0x6f)
CHOICE_OP = 0xcd

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

# ---------------- helpers ----------------
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
                tgt = norm(r[F1].split(b'\x00')[0].decode('ascii', 'replace'))
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
            if code == CHOICE_OP:
                while i < n and recs[i][0] == CHOICE_OP:
                    opt = cp(recs[i][F2].split(b'\x00')[0])
                    if opt:
                        s = opt.strip(' \u3000')
                        if s:
                            lines.append(s)
                            stat['choice'] += 1
                    i += 1
                continue
            if code == NAME_OP or code == ROW_OP:
                j = i
                if recs[j][0] == NAME_OP:
                    j += 1
                rows = []
                while j < n and recs[j][0] == ROW_OP:
                    t = cp(recs[j][F1].split(b'\x00')[0])
                    if t:
                        rows.append(strip_ruby(t))
                    j += 1
                if rows and j + 1 < n and recs[j][0] == END_OPS[0] and recs[j+1][0] == END_OPS[1]:
                    s = ''.join(rows).strip(' \u3000')
                    if s:
                        lines.append(s)
                        stat['line'] += 1
                    i = j + 2
                    continue
                # 0x6a with no rows, or rows not closed by (0x6e,0x6f): skip 1
                i = i + 1 if j == i else j
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
