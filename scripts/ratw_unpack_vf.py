"""RATW (LiveMaker) VF 解包：game.ext 目录 + game.dat 数据（offsets 相对 dat）。"""
import collections
import pathlib
import re
import sys
import zlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'tools'))
from anotherrewind_extract import VFArchive

BS = chr(92)
d = pathlib.Path('_work_ratw/[JP]Round Around the World')
vf = VFArchive((d / 'game.ext').read_bytes())
dat = (d / 'game.dat').read_bytes()
assert vf.offsets[0] == 0 and vf.offsets[-1] == len(dat), 'VF 闭合不符'
assert all(vf.offsets[i] <= vf.offsets[i + 1] for i in range(vf.count))
assert not any(vf.encflags)
out = pathlib.Path('_work_ratw/x')
bad = []
for i, n in enumerate(vf.names):
    raw = dat[vf.offsets[i]:vf.offsets[i + 1]]
    try:
        b = zlib.decompress(raw) if vf.ctypes[i] == 0 else raw
    except Exception as e:
        bad.append((n, str(e)))
        continue
    p = out / n.replace(BS, '/').lstrip('/')
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b)
print('extracted', vf.count - len(bad), '/', vf.count, 'bad', bad)
print('disk files', sum(1 for _ in out.rglob('*') if _.is_file()))
hits = [n for n in vf.names if re.search(r'dlc|追加|add|extra|特典|bonus|omake|おまけ', n, re.I)]
print('DLC-ish names:', hits)
print('txt members:', [n for n in vf.names if n.lower().endswith('.txt')])
print('lsb names:')
for n in sorted(n for n in vf.names if n.lower().endswith('.lsb')):
    print(' ', n)