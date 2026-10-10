import struct, sys, os

class Libp:
    def __init__(self, path):
        self.path = path
        self.f = open(path, 'rb')
        hdr = self.f.read(16)
        self.sig = hdr[:4]
        e1c, e2c, unk = struct.unpack_from('<III', hdr, 4)
        self.e1c, self.e2c = e1c, e2c
        raw = self.f.read(e1c*32)
        self.e1 = []
        for i in range(e1c):
            fn = raw[i*32:i*32+20]
            flags, oidx, length = struct.unpack_from('<III', raw, i*32+20)
            self.e1.append((fn.split(b'\0')[0].decode('cp932','replace'), flags, oidx, length))
        raw2 = self.f.read(e2c*4)
        self.e2 = list(struct.unpack_from('<%dI' % e2c, raw2, 0)) if e2c else []
        self.base = (16 + e1c*32 + e2c*4 + 1023) & ~1023

    def walk(self, prefix="", idx=0, count=1, out=None):
        for i in range(count):
            name, flags, oidx, length = self.e1[idx+i]
            full = prefix + "/" + name if prefix else name
            if flags & 0x10000:
                if out is not None:
                    out.append((full, length, self.base + self.e2[oidx]*1024))
            else:
                self.walk(full, oidx, length, out)

    def read_data(self, off, length):
        self.f.seek(off)
        return self.f.read(length)

if __name__ == '__main__':
    for p in sys.argv[1:]:
        lib = Libp(p)
        out = []
        lib.walk("", 0, 1, out)
        print(f"== {p}: {len(out)} files (e1c={lib.e1c} e2c={lib.e2c} base=0x{lib.base:x})")
        exts = {}
        for full, length, off in out:
            e = os.path.splitext(full)[1].lower()
            exts[e] = exts.get(e,0)+1
        print("  ext:", sorted(exts.items(), key=lambda x:-x[1]))
        # print dirs first-level and a few script-ish names
        for full, length, off in out[:0]:
            pass
        # print all non-image/audio
        for full, length, off in out:
            e = os.path.splitext(full)[1].lower()
            if e not in ('.png','.jpg','.bmp','.at9','.at3','.ogg','.mp3','.wav','.vag','.svs','.psb','.mig'):
                print(f"    {full}  len=0x{length:x}")
