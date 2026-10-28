"""XCI / NSP → 逐个 NCA 落盘（按 title 目录分），供后续流式取 romfs。"""
import os, struct, sys, shutil
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

XCI_DIR = os.path.join(os.environ.get('VNTRANS_HOME', os.getcwd()), 'src')
OUT = '_work_dcode/nca'


def find_xci():
    for f in os.listdir(XCI_DIR):
        if 'Distorted' in f and f.lower().endswith('.xci'):
            return os.path.join(XCI_DIR, f)
    raise SystemExit('xci not found')


def hfs0(fo, off):
    fo.seek(off)
    h = fo.read(0x400)
    assert h[:4] == b'HFS0', h[:4]
    n = struct.unpack('<I', h[4:8])[0]
    stsz = struct.unpack('<I', h[8:12])[0]
    st = 0x10 + n * 0x40
    ents = []
    for i in range(n):
        e = h[0x10 + i * 0x40:0x50 + i * 0x40]
        o, s, no = struct.unpack('<QQQ', e[:0x18])
        name = h[st + no:st + no + 0x40].split(b'\0')[0].decode()
        ents.append((name, o, s))
    return ents, off + st + stsz


def main():
    path = find_xci()
    size = os.path.getsize(path)
    os.makedirs(OUT, exist_ok=True)
    with open(path, 'rb') as fo:
        root, root_data = hfs0(fo, 0xF000)
        print('root', root, 'root_data', hex(root_data))
        sec_off = None
        for name, o, s in root:
            if name == 'secure':
                sec_off = root_data + o
        print('secure at', hex(sec_off))
        ents, data = hfs0(fo, sec_off)
        print('data_start', hex(data), 'remain', hex(size - data))
        for name, o, s in ents:
            abs_off = data + o
            print(name, hex(abs_off), hex(s), 'end', hex(abs_off + s))
            dst = os.path.join(OUT, '%s.nca' % name.replace('.nca', ''))
            with open(dst, 'wb') as g:
                fo.seek(abs_off)
                left = s
                while left:
                    b = fo.read(min(1 << 22, left))
                    if not b:
                        break
                    g.write(b)
                    left -= len(b)
            print('  ->', dst, os.path.getsize(dst))


main()
