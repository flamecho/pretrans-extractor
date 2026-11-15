import struct, os, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

ARCH = os.path.join(VNTRANS_HOME, '_work_voice_guy/cab/Game.rgssad')
OUT = os.path.join(VNTRANS_HOME, '_work_voice_guy/rgss')
os.makedirs(OUT, exist_ok=True)
d = open(ARCH,'rb').read()
assert d[:8] == b'RGSSAD\x00\x01'
pos = 8
magic = 0xDEADCAFE

def adv():
    global magic
    old = magic
    magic = (magic * 7 + 3) & 0xffffffff
    return old

entries = []
while pos + 4 <= len(d):
    ln = struct.unpack('<I', d[pos:pos+4])[0]; pos += 4
    ln ^= adv()
    if ln == 0 or ln > 100000: break
    name = bytearray()
    for i in range(ln):
        name.append(d[pos+i] ^ (adv() & 0xff))
    pos += ln
    name = bytes(name).decode('cp932','replace').replace('\\','/')
    size = struct.unpack('<I', d[pos:pos+4])[0]; pos += 4
    size ^= adv()
    data_start = pos
    entries.append((name, size, data_start, magic))
    pos += size

print('entries', len(entries), 'end', pos, 'total', len(d))
print('first', entries[:3]); print('last', entries[-3:])

for name, size, data_start, m in entries:
    buf = bytearray(d[data_start:data_start+size])
    k = m
    # 4-byte words
    nfull = len(buf)//4
    for i in range(nfull):
        w = int.from_bytes(buf[i*4:i*4+4], 'little') ^ k
        buf[i*4:i*4+4] = w.to_bytes(4,'little')
        k = (k*7+3)&0xffffffff
    # suffix bytes use current k shifted
    for j in range(nfull*4, len(buf)):
        buf[j] ^= (k >> ((j-nfull*4)*8)) & 0xff
    dst = os.path.join(OUT, name)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst,'wb').write(buf)
print('extracted', len(entries))
