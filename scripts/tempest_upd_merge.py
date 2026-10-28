#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""even if TEMPEST 宵闇にかく語りき魔女 Update v1.1.1（BKTR）→ 本体 romfs 合并读取。

不改 scripts/bktr_merge.py；只在其上做一处运行时修正：
  P2 的 Sec._pick 用「物理偏移处 8 字节是否为 0x50」自证密钥，本作 BKTR 段的
  romfs 头只在**虚拟** 0x898000（物理错位），自证必然失败（报「段 1 无内容密钥」）。
  ⇒ 本脚本把 _pick 换成「取第一个候选密钥」（titlekey 加密，段密钥唯一）。

用法：
  python scripts/tempest_upd_merge.py --update <upd.nsp> --base-romfs base.romfs --list
  python scripts/tempest_upd_merge.py ... --get <路径子串> --outdir DIR
  python scripts/tempest_upd_merge.py ... --new            # 只列更新档里有、本体没有的文件
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bktr_merge as P2

# ★ 修正：不要用物理偏移自证密钥
P2.Sec._pick = lambda self, hint: (self._cands()[0] if self._cands() else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--update', required=True)
    ap.add_argument('--base-romfs', required=True)
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--new', action='store_true')
    ap.add_argument('--get')
    ap.add_argument('--outdir', default='_w_upd1_yaoi/get')
    ap.add_argument('--all-changed', action='store_true')
    a = ap.parse_args()

    bdata, bfiles = P2.parse_tables(0, P2.Image(a.base_romfs).read)
    bset = set((d, n) for d, n, _, _ in bfiles)
    print('[i] 本体 romfs: data_off=%#x 文件 %d' % (bdata, len(bfiles)))

    bk, img = P2.open_update(a.update, a.base_romfs, None)
    pr = bk.patch_ranges()
    print('[i] 更新段 %d romfs_v=%#x entries=%d subs=%d patch 区间 %d 覆盖 %d B' %
          (bk.idx, bk.romfs, len(bk.entries), len(bk.subs), len(pr), sum(y - x for x, y in pr)))
    data_off, files = P2.parse_tables(bk.romfs, bk.read_v)
    print('[i] 更新 romfs 表: data_off=%#x 文件 %d' % (data_off, len(files)))

    uset = set((d, n) for d, n, _, _ in files)
    added = sorted(uset - bset)
    removed = sorted(bset - uset)
    print('[i] 新增文件 %d，消失文件 %d' % (len(added), len(removed)))
    for d, n in added:
        sz = next(s for dd, nn, _, s in files if (dd, nn) == (d, n))
        print('   + %s/%s  (%d)' % (d, n, sz))
    for d, n in removed[:20]:
        print('   - %s/%s' % (d, n))

    ch = []
    for d, nm, fo, sz in files:
        s, e = bk.romfs + data_off + fo, bk.romfs + data_off + fo + sz
        if any(s < y and x < e for x, y in pr):
            ch.append((d, nm, fo, sz))
    print('[i] 与 patch 相交的文件 %d / %d' % (len(ch), len(files)))
    for d, nm, fo, sz in sorted(ch, key=lambda x: -x[3]):
        mark = 'NEW' if (d, nm) not in bset else '   '
        print('   %s %10d  %s/%s' % (mark, sz, d, nm))

    if a.get:
        sub = a.get.lower()
        os.makedirs(a.outdir, exist_ok=True)
        n_out = 0
        for d, nm, fo, sz in files:
            full = (d + '/' + nm) if d else nm
            if sub in full.lower():
                p = os.path.join(a.outdir, full.replace('/', os.sep))
                os.makedirs(os.path.dirname(p) or '.', exist_ok=True)
                with open(p, 'wb') as w:
                    step = 1 << 23
                    base_v = bk.romfs + data_off + fo
                    for k in range(0, sz, step):
                        w.write(bk.read_v(base_v + k, min(step, sz - k)))
                print('   -> %s (%d)' % (full, sz))
                n_out += 1
        print('[i] 取出 %d 个' % n_out)


if __name__ == '__main__':
    main()
