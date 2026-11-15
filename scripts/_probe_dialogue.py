# -*- coding: utf-8 -*-
import sys
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, "tools"))
import nisenochigiri_extract as N
import cpk

CPK_PATH = os.path.join(VNTRANS_HOME, "_work_nisefd/INSTALL.cpk")
c = cpk.CPK(CPK_PATH)
c.by_name = {e['name']: e for e in c.entries if e.get('name')}
all_stcm = [e['name'] for e in c.entries
            if (e.get('name','') or '').startswith('script/') and c.raw(e)[:5] == b'STCM2']
names = set()
for fn in all_stcm:
    raw = c.raw(c.by_name[fn])
    if raw[:5] != b'STCM2': continue
    for u in N.units(raw):
        for k,t,cmd,arg in N.recs(u):
            if cmd in (0x7a,0x1dd,0x1d3) or cmd==0x1ae:
                s=N.clean(t).strip()
                if s and len(s)<=16 and N.RE_JP.search(s): names.add(s)
names.add('？？？')

TEXT_CONT={0xd2}
TEXT_END={0xd3,0x05,0x9a,0x6e,0x6f,0xd4,0x1,0xe7,0x34,0x12b,0x77,0x13,0x41dc,0x35}
NAME_OP={0x7a,0x1dd,0x1d3}

# simulate: track cur_name as engine would (name op k12 or name-box sets it)
# classify each emitted text box: had_name(set just before) vs starts_with_quote
both=0; name_noq=0; q_noname=0; none=0
name_noq_samples=[]; q_noname_samples=[]
for fn in all_stcm:
    raw=c.raw(c.by_name[fn])
    if raw[:5]!=b'STCM2': continue
    flat=[]
    for u in N.units(raw):
        for k,t,cmd,arg in N.recs(u):
            flat.append((k,t,cmd,arg))
    cur_name=None
    n=len(flat)
    for i in range(n):
        k,t,cmd,arg=flat[i]
        if k!=12:
            continue
        s=N.clean(t)
        if not s: continue
        s2=s.strip().lstrip('※')
        # name setter?
        is_name=False
        if cmd in NAME_OP:
            nm=s.strip()
            if nm and '_' not in nm and '＿' not in nm and nm in names:
                cur_name=nm; is_name=True
        # name box
        if not is_name and s2 in names:
            cur_name=s2; is_name=True
        if is_name:
            continue
        # a text box (would be emitted): check starts with quote
        st=s.lstrip('　 ')
        starts_q = st[:1] in ('「','『')
        had = cur_name is not None
        if had and starts_q: both+=1
        elif had and not starts_q:
            name_noq+=1
            if len(name_noq_samples)<15: name_noq_samples.append((fn,cur_name,s[:40]))
        elif (not had) and starts_q:
            q_noname+=1
            if len(q_noname_samples)<15: q_noname_samples.append((fn,s[:40]))
        else: none+=1
print("had_name & starts_quote (dialogue, ok):", both)
print("had_name & NO quote (suspicious speech w/o quote):", name_noq)
for x in name_noq_samples: print("  ",x)
print("NO name & starts_quote (suspicious quote w/o name):", q_noname)
for x in q_noname_samples: print("  ",x)
print("NO name & NO quote (narration, ok):", none)
