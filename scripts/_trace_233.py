import sys, collections
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
import cpk, nisenochigiri_fd_extract as F

c = cpk.CPK(os.path.join(VNTRANS_HOME, '_work_nisefd/INSTALL.cpk'))
c.by_name = {e['name']: e for e in c.entries if e.get('name')}
raw = c.raw(c.by_name['script/233'])
all_stcm = [n for n in c.by_name if n.startswith('script/') and c.raw(c.by_name[n])[:5] == b'STCM2']
names = F.load_names(c, all_stcm)
flat = []
for u in F.N.units(raw):
    for k, t, cmd, arg in F.N.recs(u):
        flat.append((k, t, cmd, arg))
# find the dup region
for i, (k, t, cmd, arg) in enumerate(flat):
    if 'そんな文句' in F.clean(t):
        s = i
        break
print('first そんな文句 at', s)
# trace from s-4 to s+8
cur = []
cur_name = None
prev = None
from collections import defaultdict
stat = defaultdict(int); stat['plate_samples'] = []; stat['_cur_file'] = 'script/233'
TEXT_CONT = F.TEXT_CONT if hasattr(F, 'TEXT_CONT') else None
TEXT_END = F.TEXT_END if hasattr(F, 'TEXT_END') else None
NAME_OP = F.NAME_OP
print('NAME_OP=', NAME_OP, 'TEXT_END=', TEXT_END)
for idx in range(max(0, s-4), min(len(flat), s+9)):
    k, t, cmd, arg = flat[idx]
    s_clean = F.clean(t)
    # replicate the decision logic minimally to see path
    path = '?'
    if k != 12:
        path = 'skip(k!=12)'; continue
    if cmd in NAME_OP:
        nm = F.clean(t).strip()
        if nm and '_' not in nm and '＿' not in nm and nm in names:
            cur_name = nm; path = 'NAME_OP->name'; stat['plate_op']+=1;
        elif cmd != 0xd3:
            path = 'NAME_OP->skip(nonname)'; stat['plate_op']+=1
        else:
            path = 'NAME_OP->fallthrough(0xd3 nonname)'
    if path == '?':
        if not s_clean:
            path = 'empty'
        elif F.is_name_head(s_clean, (flat[idx+1][1][:1] if idx+1<len(flat) else ''), names):
            cur_name = s_clean.strip().lstrip('※'); path = 'name_head'
        elif cmd in TEXT_CONT:
            cur.append(s_clean); path = 'TEXT_CONT->append'
        elif cmd in TEXT_END:
            if s_clean.strip(): cur.append(s_clean)
            if cur:
                txt=''.join(cur); del cur[:]
                st=txt.lstrip('　 ')
                if st[:1] in ('「','『') and cur_name is not None:
                    line=cur_name+txt; new_name=cur_name
                else:
                    line=txt; new_name=None
                print('   EMIT L:', repr(line[:60])); prev=line; cur_name=new_name
                path='TEXT_END->emit'
        else:
            path='other'
    print(f'  {idx:4d} k={k:3d} cmd={cmd:#06x} clean={s_clean[:40]!r} => {path} cur_name={cur_name!r}')
