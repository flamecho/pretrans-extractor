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

# (A) categorize the 195 orphans
dst=os.path.join(VNTRANS_HOME, "提取结果/[PSP-JP]二世の契り 想い出の先へ.txt")
lines=open(dst,encoding='utf-8-sig').read().split('\n')
orphan=[l for l in lines if l.lstrip('　 ')[:1] in ('「','『')]
sys_pat = re.compile(r'(大吉|中吉|小吉|吉|末吉|凶|大凶|マップイベント|いたずら|飴を|おみくじ|選ぶ|〜|～)')
sysc=sum(1 for l in orphan if sys_pat.search(l))
print("orphans total:", len(orphan), " system-ish:", sysc, " other:", len(orphan)-sysc)
print("--- non-system orphans (speech-like, possibly missed name) ---")
shown=0
for l in orphan:
    if not sys_pat.search(l):
        print("  ", l[:80])
        shown+=1
        if shown>=30: break

# (B) context of a speech-like orphan: 知り合って間もないのに
print("\n=== context of '知り合って間もないのに' ===")
for fn in all_stcm:
    raw=c.raw(c.by_name[fn])
    flat=[]
    for u in N.units(raw):
        for k,t,cmd,arg in N.recs(u): flat.append((k,t,cmd,arg))
    for i,(k,t,cmd,arg) in enumerate(flat):
        if t and '知り合って間もないのに' in t:
            for j in range(max(0,i-12), min(len(flat),i+2)):
                kk,tt,cc,aa=flat[j]
                print(j, "k=%d cmd=%s %r"%(kk, hex(cc) if isinstance(cc,int) else cc, (N.clean(tt)[:46] if tt else '')))
            break
    else:
        continue
    break
