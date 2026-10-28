#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""seisyun_extract.py —— 《青春はじめました！》脚本 .bin → 一行一次点击的文本。

口径：
  收：DOC（正文/独白/台词，一次性点击一屏）、SLMS（选项）
  弃：DILG（名札，整行丢弃、不加前缀）、其余全为演出指令
  弃：MEM_*（REPLAY_*＝回想重播，与正篇 100% 重复）、z_*（z_mes_only 等调试/测试脚本）
  同框软换行（DOC 内 \\n）合并为一行，续行行首的全角缩进 　 去掉。
"""
import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seisyun_bin as SB

SKIP_RE = re.compile(r'^(mem_|z|zzz|select|wather)', re.I)   # 回想重播 / 调试·测试脚本


def natkey(p):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', p)]


def clean(raw):
    """cp932 解码 + 去尾部 NUL + 同框软换行合并（\n 直接去掉，保留行首全角缩进）。"""
    s = raw.split(b'\0')[0].decode('cp932', 'replace')
    if not s:
        return ''
    return s.replace('\n', '').strip()


def extract(src, disc):
    files = sorted(glob.glob(os.path.join(src, '*.bin')), key=lambda p: natkey(os.path.basename(p)))
    lines = []
    st = {'files_total': len(files), 'files_used': 0, 'skipped': [],
          'doc': 0, 'opt': 0, 'empty': 0, 'per_prefix': {}}
    for f in files:
        b = os.path.basename(f)
        pre = b.split('_')[0]
        if SKIP_RE.match(b):
            st['skipped'].append(b)
            continue
        ev = SB.events(f)
        n0 = len(lines)
        st['files_used'] += 1
        for tag, code, fs in ev:
            if tag == 'DOC':
                t = clean(SB.field(fs, 'Text') or b'')
                if not t:
                    st['empty'] += 1
                    continue
                lines.append(t)
                st['doc'] += 1
            elif tag == 'SLMS':
                t = clean(SB.field(fs, 'Docu') or b'')
                if t:
                    lines.append(t)
                    st['opt'] += 1
        st['per_prefix'][pre] = st['per_prefix'].get(pre, 0) + len(lines) - n0
    return lines, st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--disc', required=True)
    ap.add_argument('--stats')
    a = ap.parse_args()
    lines, st = extract(a.src, a.disc)
    with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as o:
        o.write('\n'.join(lines))
        o.write('\n')
    st['lines'] = len(lines)
    st['bytes'] = os.path.getsize(a.out)
    st['disc'] = a.disc
    print(json.dumps({k: v for k, v in st.items() if k != 'per_prefix'},
                     ensure_ascii=False, indent=2))
    print('per_prefix:', json.dumps(st['per_prefix'], ensure_ascii=False))
    if a.stats:
        json.dump(st, open(a.stats, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
