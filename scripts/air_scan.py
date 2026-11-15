"""批量反汇编所有方法，按「字节运算 + ByteArray 读写」特征筛解密候选。"""
import sys
import collections

sys.path.insert(0, 'tools')
sys.path.insert(0, '_work_rakido')
import air_abc as A
import air_body as B
import sh as SH

d = B.abc_bytes('_work_rakido/app.swf')
bodies = B.find_bodies(d)
S = SH.Sh()

KEY = ('readByte', 'writeByte', 'readUnsignedByte', 'writeUnsignedByte',
       'readBytes', 'writeBytes', 'bitxor', 'bitand', 'bitor', 'lshift',
       'urshift', 'rshift', 'readUnsignedInt', 'writeUnsignedInt',
       'readInt', 'readShort', 'readUTF', 'readUTFBytes', 'inflate', 'uncompress')

rows = []
for rec, cs, cl, mid in bodies:
    out = A.disasm(S, d[cs:cs + cl])
    if not out:
        continue
    names = collections.Counter()
    for at, txt in out:
        op = txt.split()[0] if txt else ''
        names[op] += 1
    hits = sum(names[k] for k in KEY if k in names)
    if hits == 0:
        continue
    score = 0
    if names.get('bitxor'):
        score += 10 * names['bitxor']
    if names.get('add') or names.get('subtract'):
        score += 0
    if names.get('readByte') or names.get('writeByte'):
        score += 5
    if names.get('lshift') or names.get('urshift'):
        score += 3
    rows.append((score, mid, cs, cl, len(out), dict(names)))

rows.sort(reverse=True)
print('methods with IO/bit ops: %d' % len(rows))
for score, mid, cs, cl, ni, nm in rows[:18]:
    picked = {k: v for k, v in nm.items() if k in KEY}
    print('\nscore=%-3d method=%-5d code=%#x len=%-5d insns=%-4d %s'
          % (score, mid, cs, cl, ni, picked))
