# -*- coding: utf-8 -*-
import sys, re
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, "tools"))
import cpk
CPK_PATH = os.path.join(VNTRANS_HOME, "_work_nisefd/INSTALL.cpk")
c = cpk.CPK(CPK_PATH)
c.by_name = {e['name']: e for e in c.entries if e.get('name')}

def jp_runs(raw, maxshow=900):
    t = raw.decode('cp932','ignore')
    # show runs of JP + ascii + common punct
    out=[]
    cur=[]
    for ch in t:
        if re.match(r'[぀-ヿ一-龠０-９Ａ-Ｚａ-ｚA-Za-z0-9、。！？・『』「」\s：:（）()／/-]', ch):
            cur.append(ch)
        else:
            if cur: out.append(''.join(cur)); cur=[]
    if cur: out.append(''.join(cur))
    # filter runs length>=2 with JP
    jp=[r for r in out if len(r)>=2 and re.search(r'[぀-ヿ一-龠]', r)]
    return jp

for fn in ['script/42','script/15','script/12','script/13','script/14','script/16','script/40','script/41']:
    raw=c.raw(c.by_name[fn])
    runs=jp_runs(raw)
    print("\n########## %s (size=%d, jp_runs=%d) ##########" % (fn, len(raw), len(runs)))
    shown=0
    for r in runs:
        print("  ", repr(r[:80]))
        shown+=1
        if shown>=25: print("  ... (%d more)"% (len(runs)-shown)); break
