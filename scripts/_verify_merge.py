# -*- coding: utf-8 -*-
import sys, re
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, "tools"))
import nisenochigiri_extract as N
import cpk
import nisenochigiri_fd_extract as F

CPK_PATH = os.path.join(VNTRANS_HOME, "_work_nisefd/INSTALL.cpk")
c = cpk.CPK(CPK_PATH)
c.by_name = {e['name']: e for e in c.entries if e.get('name')}
all_stcm = [e['name'] for e in c.entries
            if (e.get('name','') or '').startswith('script/') and c.raw(e)[:5] == b'STCM2']
names = F.load_names(c, all_stcm)
stat = {'frame':0,'opt':0,'plate_op':0,'plate_txt':0,'dup':0,'plate_samples':[],
        'opt_noise':[],'credit':0,'skip':0,'opt_dup':0,'cg_label':0,'_cur_file':None}

# (1) script/100 prologue: show first 25 emitted lines, flag any >120 chars (merge symptom)
print("=== script/100 first 30 emitted lines ===")
seg = F.extract_file(c.raw(c.by_name['script/100']), names, stat)
cnt=0
for l in seg:
    if not l.strip(): continue
    mark = "  <-- LONG?" if len(l)>120 else ""
    print(repr(l[:130])+mark)
    cnt+=1
    if cnt>=30: break

# (2) orphan dialogue: lines that START with 「/『 but first char is 「 (no name prefix)
dst=os.path.join(VNTRANS_HOME, "提取结果/[PSP-JP]二世の契り 想い出の先へ.txt")
lines=open(dst,encoding='utf-8-sig').read().split('\n')
orphan=[]
for l in lines:
    st=l.lstrip('　 ')
    if st[:1] in ('「','『'):   # dialogue-candidate
        # name prefix would be <name>「 ; here st already starts with quote => no name
        orphan.append(l)
print("\n=== dialogue lines starting directly with 「/『 (no name prefix) ===")
print("count:", len(orphan))
for l in orphan[:25]: print("  ", l[:70])
