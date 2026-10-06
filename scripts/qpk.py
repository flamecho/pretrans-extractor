"""QuinRose / Qoo-framework QPK/QPI archive reader (PSP).

Format (per Garbro ArcQPK.cs + about-qoo):
  QPI index:
    char magic[4]  "QPI\0"
    int32  count            @4   (number of offset/size entries)
    (20 bytes of version/padding, ignored)
    entries start @0x1C, each = uint32 offset + uint32 size  (8 bytes)
        size & 0x80000000 -> skip (instruction placeholder, not a file)
        size & 0x40000000 -> CZL compressed
        unpacked size      = size & 0x3FFFFFFF
  QPK data:
    entry data at `offset`
    if packed and starts with "CZL\0":
        uint32 compSize @+4   (size of the zlib stream)
        uint32 decompSize @+8 (expected decompressed size)
        zlib stream @+12
    else: raw block of on-disk size (next entry offset - this offset)
"""
import struct
import zlib


class QPK:
    def __init__(self, qpi_path, qpk_path):
        with open(qpi_path, "rb") as f:
            self.d = f.read()
        with open(qpk_path, "rb") as f:
            self.qpk = f.read()
        if self.d[:4] != b"QPI\x00":
            raise ValueError("not a QPI index: %r" % self.d[:4])
        self.count = struct.unpack("<i", self.d[4:8])[0]
        real = []
        for i in range(self.count):
            p = 0x1C + i * 8
            if p + 8 > len(self.d):
                break
            off, size = struct.unpack("<II", self.d[p:p + 8])
            if (size & 0x80000000) or size == 0:
                continue
            real.append((off, size))
        real_sorted = sorted(real)
        ondisk = {}
        last = len(self.qpk)
        for off, size in reversed(real_sorted):
            ondisk[off] = last - off
            last = off
        self.entries = []
        for off, size in real:
            self.entries.append({
                "off": off,
                "orig": size,
                "packed": bool(size & 0x40000000),
                "unpacked": size & 0x3FFFFFFF,
                "ondisk": ondisk[off],
            })

    def extract(self, entry):
        off = entry["off"]
        if entry["packed"] and self.qpk[off:off + 4] == b"CZL\x00":
            comp = struct.unpack("<I", self.qpk[off + 4:off + 8])[0]
            end = min(off + 12 + comp, len(self.qpk))
            return zlib.decompress(self.qpk[off + 12:end])
        return self.qpk[off:off + entry["ondisk"]]

    def iter_scripts(self):
        """Yield decoded text of every entry that looks like a KAG scenario
        (contains [message] or [select])."""
        for e in self.entries:
            try:
                raw = self.extract(e)
            except Exception:
                continue
            txt = None
            for enc in ("cp932", "utf-8", "utf-8-sig"):
                try:
                    txt = raw.decode(enc)
                    break
                except Exception:
                    continue
            if txt is None:
                continue
            if "[message" not in txt and "[select" not in txt:
                continue
            yield txt
