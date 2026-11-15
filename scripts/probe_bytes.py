import sys
sys.path.insert(0,'tools')
import cpk, nisenochigiri_extract as N
src=open('scripts/nisenochigiri_extract.py','rb').read().decode('utf-8','ignore')
import re
# print the units/recs function bodies
for fn in ('def units','def recs','TEXT_CONT','TEXT_END','NAME_OP'):
    idx=src.find(fn)
    print('====',fn,'====')
    print(src[idx:idx+1600])
    print()
