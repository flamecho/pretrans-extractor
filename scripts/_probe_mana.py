import sys, re
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
import cpk, nisenochigiri_fd_extract as F

c = cpk.CPK(os.path.join(VNTRANS_HOME, '_work_nisefd/INSTALL.cpk'))
c.by_name = {e['name']: e for e in c.entries if e.get('name')}
needle = 'テレビや写真でしか見たことなくて'.encode('cp932')

# find which script file holds the needled text
hit = None
for fn, e in c.by_name.items():
    if not fn.startswith('script/'):
        continue
    raw = c.raw(e)
    if needle in raw:
        hit = fn
        break
print('FILE:', hit)
raw = c.raw(c.by_name[hit])
pos = raw.find(needle)
print('needle at', pos)

# show records in a window around it
flat = []
for u in F.N.units(raw):
    for k, t, cmd, arg in F.N.recs(u):
        flat.append((k, t, cmd, arg))
print('total records', len(flat))
# find idx whose text contains the needle
for i, (k, t, cmd, arg) in enumerate(flat):
    s = F.clean(t)
    if 'テレビや写真' in s:
        print('--- target idx', i, 'k', k, 'cmd', hex(cmd))
        # dump surrounding 12 records raw text + clean
        for j in range(max(0, i-12), min(len(flat), i+4)):
            kk, tt, cc, aa = flat[j]
            ss = F.clean(tt)
            tag = ''
            if kk == 12 and ss in F.load_names(c, [fn for fn in c.by_name if fn.startswith('script/') and c.raw(c.by_name[fn])[:5]==b'STCM2']):
                tag = ' [name?]'
            print(f'  {j:3d} k={kk:3d} cmd={cc:#06x} raw={tt[:30]!r} clean={ss[:40]!r}{tag}')
        break
