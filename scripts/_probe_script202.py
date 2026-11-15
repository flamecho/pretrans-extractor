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
raw = c.raw(c.by_name['script/202'])
flat=[]
for u in N.units(raw):
    for k,t,cmd,arg in N.recs(u):
        flat.append((k,t,cmd,arg))
# find the quoted line
target='急なことで皆を驚かせてしまったが'
for i,(k,t,cmd,arg) in enumerate(flat):
    if target in (t or ''):
        print("=== hit at idx",i,"===")
        for j in range(max(0,i-18), min(len(flat), i+3)):
            kk,tt,cc,aa=flat[j]
            print(j, "k=%d cmd=%s %r" % (kk, hex(cc) if isinstance(cc,int) else cc, (N.clean(tt)[:50] if tt else '')))
        break
