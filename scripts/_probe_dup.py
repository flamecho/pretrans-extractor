import sys
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
import cpk, nisenochigiri_fd_extract as F

c = cpk.CPK(os.path.join(VNTRANS_HOME, '_work_nisefd/INSTALL.cpk'))
c.by_name = {e['name']: e for e in c.entries if e.get('name')}
needle = '考えてみたら'.encode('cp932')
hits = [n for n in c.by_name if n.startswith('script/') and needle in c.raw(c.by_name[n])]
print('files:', hits)
for fn in hits:
    raw = c.raw(c.by_name[fn])
    flat = []
    for u in F.N.units(raw):
        for k, t, cmd, arg in F.N.recs(u):
            flat.append((k, t, cmd, arg))
    for i, (k, t, cmd, arg) in enumerate(flat):
        s = F.clean(t)
        if '考えてみたら' in s:
            print('====', fn, 'idx', i, '====')
            for j in range(max(0, i-4), min(len(flat), i+4)):
                kk, tt, cc, aa = flat[j]
                print(f'  {j:4d} k={kk:3d} cmd={cc:#06x} clean={F.clean(tt)!r}')
            break
