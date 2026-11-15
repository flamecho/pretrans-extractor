import sys
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
import cpk, nisenochigiri_fd_extract as F

c = cpk.CPK(os.path.join(VNTRANS_HOME, '_work_nisefd/INSTALL.cpk'))
c.by_name = {e['name']: e for e in c.entries if e.get('name')}

# build full name set for the file
all_stcm = [n for n in c.by_name if n.startswith('script/') and c.raw(c.by_name[n])[:5] == b'STCM2']
names = F.load_names(c, all_stcm)

for fn in ('script/101',):
    raw = c.raw(c.by_name[fn])
    flat = []
    for u in F.N.units(raw):
        for k, t, cmd, arg in F.N.recs(u):
            flat.append((k, t, cmd, arg))
    # locate boxes containing 馬なんて
    idxs = [i for i, (k, t, cmd, arg) in enumerate(flat) if '馬なんて' in F.clean(t)]
    print('file', fn, 'records', len(flat), 'matches', idxs)
    for i in idxs:
        print('==== target idx', i, '====')
        for j in range(max(0, i-14), min(len(flat), i+3)):
            k, t, cmd, arg = flat[j]
            s = F.clean(t)
            nameflag = ''
            if k == 12 and s.strip().lstrip('※') in names:
                nameflag = ' <IN-NAMES>'
            if F.is_name_head(s, (flat[j+1][1][:1] if j+1 < len(flat) else ''), names):
                nameflag += ' <NAME_HEAD>'
            print(f'  {j:4d} k={k:3d} cmd={cmd:#06x} clean={s[:46]!r}{nameflag}')
