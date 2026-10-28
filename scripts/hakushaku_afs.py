"""CRI AFS (\x00SFA) minimal extractor for 5pb PS2 titles."""
import os
import struct
import sys


def extract(path, outdir):
    d = open(path, 'rb').read()
    assert d[:4] == b'AFS\0', d[:4]
    n = struct.unpack_from('<I', d, 4)[0]
    os.makedirs(outdir, exist_ok=True)
    for i in range(n):
        off, size = struct.unpack_from('<II', d, 8 + i * 8)
        if size == 0:
            continue
        open(os.path.join(outdir, '%05d.bin' % i), 'wb').write(d[off:off + size])
    print(path, 'files:', n)


if __name__ == '__main__':
    extract(sys.argv[1], sys.argv[2])
