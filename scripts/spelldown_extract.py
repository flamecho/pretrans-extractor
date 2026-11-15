import struct, re, bisect, collections, os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

BASE = os.path.join(VNTRANS_HOME, "_work_spelldown")
M = open(BASE + r"\iso1\setupdata\Data\SD_MSG.dat", 'rb').read()
D = open(BASE + r"\iso1\setupdata\Data\SD_SNR.dat", 'rb').read()

cnt = struct.unpack_from('<I', M, 6)[0]
pool = struct.unpack_from('<I', M, 0x0a)[0]
st = len(M) - pool
recs = []
for i in range(cnt):
    rel = struct.unpack_from('<I', M, 0x0e + 4 * i)[0]
    off = st + rel
    n = struct.unpack_from('<I', M, off)[0]
    recs.append(bytes(b ^ 0xff for b in M[off + 4:off + 4 + n]).decode('cp932'))

# message reference positions (L0/L1)
msgpos = []
i = 0
while True:
    j = D.find(b'\x00\x80', i)
    if j < 0:
        break
    v = struct.unpack_from('<I', D, j + 2)[0]
    if v < cnt:
        msgpos.append((j, v))
    i = j + 1
assert len(msgpos) == cnt and [v for _, v in msgpos] == list(range(cnt))

# option entries
opts = []
i = 0
while True:
    j = D.find(b'\x28\x00\x01', i)
    if j < 0:
        break
    if j + 5 <= len(D):
        ln = struct.unpack_from('<H', D, j + 3)[0]
        if 0 < ln <= 400 and ln % 2 == 0 and j + 5 + ln <= len(D):
            try:
                t = D[j + 5:j + 5 + ln].decode('cp932')
                opts.append((j, ln, t))
            except Exception:
                pass
    i = j + 1

# attach each option to the message index immediately before it
pos = [p for p, _ in msgpos]
menus = collections.OrderedDict()
for j, ln, t in opts:
    k = bisect.bisect_right(pos, j)
    prev = msgpos[k - 1][1]
    menus.setdefault(prev, []).append((j, ln, t))

# verify each option lies between its prev message and the next message
for prev, items in menus.items():
    nxtpos = pos[bisect.bisect_right(pos, items[0][0])]
    for a, b in zip(items, items[1:]):
        assert a[0] < b[0]
    for j, ln, t in items:
        assert j > pos[bisect.bisect_right(pos, j) - 1]
        assert j < nxtpos
    print("menu prev", prev, "n", len(items), [x[2] for x in items])

print("menus", len(menus), "options", sum(len(v) for v in menus.values()))

TAG_A = re.compile(r'\\a([^;]*);')
TAG_V = re.compile(r'\\v[^;]*;')


def process(t):
    m = TAG_A.match(t)
    name = m.group(1) if m else ''
    t = TAG_A.sub('', t)
    t = TAG_V.sub('', t)
    t = t.replace('\\n', '').replace('\\k', '')
    t = t.replace('\t', '\u3000')
    assert '\\' not in t, repr(t)
    return name + t


lines = []
for i, t in enumerate(recs):
    lines.append(process(t))
    if i in menus:
        for _, _, ot in menus[i]:
            lines.append(ot)

print("lines", len(lines))

out = BASE + r"\_out.txt"
with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
    f.write('\n'.join(lines) + '\n')
print("written", out, os.path.getsize(out))

# stats
q_open = sum(1 for l in lines if l.count('「') > l.count('」'))
q_close = sum(1 for l in lines if l.count('」') > l.count('「'))
p_open = sum(1 for l in lines if l.count('（') > l.count('）'))
p_close = sum(1 for l in lines if l.count('）') > l.count('（'))
print("unbalanced 「", q_open, "」", q_close, "（", p_open, "）", p_close)
print("empty", sum(1 for l in lines if not l.strip()))
print("max len", max(len(l) for l in lines))
print("ctrl", sum(1 for l in lines for c in l if ord(c) < 32))
print("u3000-start", sum(1 for l in lines if l.startswith('\u3000')))
