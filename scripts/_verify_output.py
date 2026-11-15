# -*- coding: utf-8 -*-
import sys, re
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
# rebuild names exactly like extractor
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

# 1) Label-leak check on output
dst=os.path.join(VNTRANS_HOME, "提取结果/[PSP-JP]二世の契り 想い出の先へ.txt")
lines=open(dst,encoding='utf-8-sig').read().split('\n')
leak=[l for l in lines if re.match(r'^(bg|ev|masatora|suien|ayahime)\b', l)]
print("label-leak lines (bg/ev/masatora/...):", len(leak))
for l in leak[:10]: print("  ", l[:60])

# 2) 水輪 prefix on non-quote lines
mizu=[l for l in lines if l.startswith('水輪') and not l.startswith('水輪「') and not l.startswith('水輪『')]
print("水輪-prefixed non-dialogue lines:", len(mizu))
for l in mizu[:10]: print("  ", l[:60])

# 3) name-prefixed lines whose content does NOT start with 「/『 (potential mis-prefix)
bad=[]
for l in lines:
    # name prefix = leading run of JP chars (no 「『 at very start)
    if l[:1] in ('「','『'): continue
    # strip leading fullwidth/half space
    st=l.lstrip('　 ')
    if st[:1] in ('「','『'): continue
    # does it contain a 「 later with a name-looking prefix?
    # heuristic: line begins with a known name token then content without leading 「
    # find first 「
    m=re.search(r'[「『]', st)
    if m and m.start()>0:
        pref=st[:m.start()].strip()
        # if pref is a known name or looks like one (has JP, no space, short), flag
        if pref and len(pref)<=12 and re.search(r'[぀-ヿ一-龠]', pref) and '　' not in pref:
            bad.append(l)
print("name-prefix + non-leading-quote lines (suspicious):", len(bad))
for l in bad[:20]: print("  ", l[:70])
