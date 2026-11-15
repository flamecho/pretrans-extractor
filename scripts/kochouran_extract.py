"""Otomedou Kochouran: strict XP3 reader and game-specific KAG extraction."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import struct
import zlib


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def decode_script(data):
    if data.startswith(b'\xff\xfe'):
        return data.decode('utf-16'), 'utf-16le-bom'
    if data.startswith(b'\xef\xbb\xbf'):
        return data.decode('utf-8-sig'), 'utf-8-bom'
    return data.decode('cp932'), 'cp932'


class XP3:
    def __init__(self, path):
        self.path = Path(path)
        self.entries = {}
        self.index_blocks = []
        with self.path.open('rb') as f:
            assert f.read(11) == b'XP3\r\n \n\x1a\x8bg\x01'
            pos = struct.unpack('<Q', f.read(8))[0]
            seen = set()
            while True:
                assert pos not in seen
                seen.add(pos)
                f.seek(pos)
                flag = f.read(1)[0]
                stored = struct.unpack('<Q', f.read(8))[0]
                original = struct.unpack('<Q', f.read(8))[0] if flag & 1 else stored
                raw = f.read(stored)
                assert len(raw) == stored
                data = zlib.decompress(raw) if flag & 1 else raw
                assert len(data) == original
                self.index_blocks.append(dict(offset=pos, flags=flag, stored=stored, original=original))
                for tag, payload in self.chunks(data):
                    assert tag == b'File', tag
                    ent = dict(segments=[], extra=[])
                    for kind, p in self.chunks(payload):
                        if kind == b'info':
                            flags, size, archived, nlen = struct.unpack_from('<IQQH', p)
                            assert len(p) == 22 + 2 * nlen
                            ent.update(name=p[22:].decode('utf-16le'), flags=flags, size=size, archived=archived)
                        elif kind == b'segm':
                            assert len(p) % 28 == 0
                            ent['segments'] = [struct.unpack_from('<IQQQ', p, q) for q in range(0, len(p), 28)]
                        elif kind == b'adlr':
                            assert len(p) == 4
                            ent['adler'] = struct.unpack('<I', p)[0]
                        else:
                            ent['extra'].append(dict(tag=kind.decode('ascii'), size=len(p)))
                    assert ent['name'] not in self.entries
                    assert sum(s[2] for s in ent['segments']) == ent['size']
                    assert sum(s[3] for s in ent['segments']) == ent['archived']
                    for fl, off, orig, packed in ent['segments']:
                        assert fl in (0, 1)
                        assert 0 <= off <= off + packed <= self.path.stat().st_size
                    self.entries[ent['name']] = ent
                if not flag & 0x80:
                    break
                pos = struct.unpack('<Q', f.read(8))[0]

    @staticmethod
    def chunks(data):
        p = 0
        while p < len(data):
            assert p + 12 <= len(data)
            tag = data[p:p + 4]
            size = struct.unpack_from('<Q', data, p + 4)[0]
            assert p + 12 + size <= len(data)
            yield tag, data[p + 12:p + 12 + size]
            p += 12 + size
        assert p == len(data)

    def read(self, name):
        ent = self.entries[name]
        parts = []
        with self.path.open('rb') as f:
            for flag, offset, original, stored in ent['segments']:
                f.seek(offset)
                raw = f.read(stored)
                assert len(raw) == stored
                part = zlib.decompress(raw) if flag & 1 else raw
                assert len(part) == original
                parts.append(part)
        data = b''.join(parts)
        assert len(data) == ent['size']
        assert zlib.adler32(data) & 0xffffffff == ent['adler'], name
        return data


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--game', type=Path, required=True)
    ap.add_argument('--work', type=Path, required=True)
    args = ap.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    x = XP3(args.game / 'data.xp3')
    write_json(args.work / 'archive.json', dict(index_blocks=x.index_blocks, entries=list(x.entries.values())))
    types = collections.Counter(Path(n).suffix.lower() for n in x.entries)
    scripts = []
    for n in x.entries:
        if Path(n).suffix.lower() in ('.ks', '.tjs', '.txt', '.csv', '.ini', '.asd', '.sli'):
            data = x.read(n)
            dst = args.work / 'unpacked' / n
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
            t, enc = decode_script(data)
            utf = args.work / 'utf8' / n
            utf.parent.mkdir(parents=True, exist_ok=True)
            utf.write_text(t.replace('\r\n', '\n').replace('\r', '\n'), encoding='utf-8', newline='\n')
            scripts.append(dict(name=n, size=len(data), encoding=enc, sha256=hashlib.sha256(data).hexdigest()))
    write_json(args.work / 'scripts.json', scripts)
    print('index', x.index_blocks, 'members', len(x.entries), 'types', dict(types))
    print('decoded scripts', len(scripts), 'sample', scripts[:12])


if __name__ == '__main__':
    main()
