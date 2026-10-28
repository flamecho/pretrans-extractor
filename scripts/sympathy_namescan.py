#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统计正文里的 #Name 宏与候选默认名。"""
import sys, os, glob, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sympathy_extract import walk, BODY, VARIANT

files = sorted(glob.glob(os.path.join(sys.argv[1], '*.DAT')))
n = 0
for f in files:
    d = open(f, 'rb').read()
    for op, ss in walk(d):
        if op in BODY or op in VARIANT:
            for s in ss:
                if s and '#Name' in s:
                    n += 1
                    print(os.path.basename(f), hex(op), s[:70])
print('total', n)
