#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""いざ、出陣！恋戦 第二幕 甲斐編 —— 批量解壳 + PSB 反编译。

1) 用 btf_mdf.mdf_decrypt 把 scenario_body.bin 的每个成员解开（seed = 成员名 + .scn.m）
2) 调 PsbDecompile.exe 把 PSB 转 JSON
"""
import json
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
from btf_mdf import mdf_decrypt

KEY = '9362abe723sfe'
ROOT = (os.path.abspath(sys.argv[1]) if len(sys.argv) > 1
        else os.path.dirname(os.path.abspath(__file__)))
BODY = os.path.join(ROOT, 'scenario_body.bin')
INFO = os.path.join(ROOT, 'scenario_info.psb.m.json')
DEC = os.path.join(ROOT, 'dec')
PSBDEC = os.path.join(VNTRANS_HOME, 'scripts/freemote/PsbDecompile.exe')


def main():
    os.makedirs(DEC, exist_ok=True)
    body = open(BODY, 'rb').read()
    info = json.load(open(INFO, encoding='utf-8-sig'))['file_info']

    jobs = []
    for name, (off, size) in info.items():
        dst = os.path.join(DEC, name + '.psb')
        if os.path.exists(dst) and os.path.getsize(dst) > 8:
            jobs.append((dst, False))
            continue
        try:
            plain = mdf_decrypt(body[off:off + size], KEY, name + '.scn.m', 131)
        except Exception as e:  # noqa: BLE001
            print('MDF FAIL', name, e)
            continue
        if not plain.startswith(b'PSB\x00'):
            print('NOT PSB', name, plain[:8])
            continue
        open(dst, 'wb').write(plain)
        jobs.append((dst, True))

    print('members', len(jobs), 'newly unpacked', sum(1 for _, n in jobs if n))

    def decomp(p):
        json_path = p[:-4] + '.json'
        if os.path.exists(json_path):
            return
        subprocess.run([PSBDEC, p], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=False)

    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(decomp, [p for p, _ in jobs]))
    print('json', sum(1 for p, _ in jobs if os.path.exists(p[:-4] + '.json')), '/', len(jobs))


if __name__ == '__main__':
    main()
