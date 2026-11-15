# -*- coding: utf-8 -*-
import sys, re
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, "tools"))
import cpk
CPK_PATH = os.path.join(VNTRANS_HOME, "_work_nisefd/INSTALL.cpk")
c = cpk.CPK(CPK_PATH)
c.by_name = {e['name']: e for e in c.entries if e.get('name')}
all_script = sorted([e['name'] for e in c.entries
                     if (e.get('name','') or '').startswith('script/')])
print("total script/* entries:", len(all_script))
stcm = [f for f in all_script if c.raw(c.by_name[f])[:5] == b'STCM2']
non_stcm = [f for f in all_script if c.raw(c.by_name[f])[:5] != b'STCM2']
EXCLUDE = {'script/0','script/1','script/2','script/3','script/4','script/5','script/6',
 'script/7','script/18','script/19','script/20','script/21','script/45','script/86',
 'script/99','script/200','script/3000','script/999','script/70','script/71','script/72',
 'script/73','script/74','script/75','script/80','script/81','script/82','script/83',
 'script/84','script/85','script/87','script/998'}
print("STCM2 total:", len(stcm), " non-STCM2:", len(non_stcm))
print("  extracting:", len([f for f in stcm if f not in EXCLUDE]),
      " gallery(EXCLUDE&STCM2):", len([f for f in stcm if f in EXCLUDE]))

RE_JP = re.compile(r'[぀-ヿ一-龠]')
def jp_bytes(raw):
    # count cp932-decoded JP runs (rough heuristic)
    try:
        t = raw.decode('cp932','ignore')
    except: t=''
    return len(RE_JP.findall(t))

print("\n=== non-STCM2 files (fully excluded): JP content? ===")
for f in non_stcm:
    raw=c.raw(c.by_name[f])
    n=jp_bytes(raw)
    print("  %-14s size=%-8d jp_chars=%d  head=%r" % (f, len(raw), n, raw[:8]))

print("\n=== EXCLUDE_FILES (STCM2, gallery/system): JP content? ===")
for f in sorted([x for x in stcm if x in EXCLUDE]):
    raw=c.raw(c.by_name[f])
    n=jp_bytes(raw)
    print("  %-14s size=%-8d jp_chars=%d" % (f, len(raw), n))
