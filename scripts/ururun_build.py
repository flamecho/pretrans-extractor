#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""うるるんクエスト 恋遊記 全文本生成：VML -> 提取结果/*.txt"""
import glob
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ururun_vml as U

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, '_work_urun', 'adv')
DST = os.path.join(ROOT, '提取结果', '[PS2-JP]うるるんクエスト 恋遊記.txt')

# 共通導入塊：正文完全相同（md5 全等）的副本文件，只留自然序首个
FOLD = {'S082.VML': 'S035.VML', 'S083.VML': 'S035.VML', 'S084.VML': 'S035.VML',
        'S216.VML': 'S207.VML', 'S226.VML': 'S207.VML', 'S237.VML': 'S207.VML',
        'S257.VML': 'S207.VML', 'S266.VML': 'S207.VML', 'S400.VML': 'S207.VML'}

# 系统・UI（道具入手 / 仲間加入 / おまけ解锁 / 玩法说明弹窗）——不渲染为剧情文本
SYS = re.compile(r'(を手に入れた！$|が仲間に加わった！$|追加されました|可能になりました'
                 r'|「パオ」の使い方)')


def main():
    lines, folded, dropped = [], [], 0
    for f in sorted(glob.glob(os.path.join(SRC, '*.VML')), key=U.natkey):
        b = os.path.basename(f)
        if b in FOLD:
            folded.append((b, FOLD[b]))
            continue
        for k, s in U.load(f):
            t = U.tidy(s)
            if not t:
                continue
            if k == 'T' and SYS.search(t):
                dropped += 1
                continue
            lines.append(t)
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    with io.open(DST, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('行数', len(lines), '折叠文件', len(folded), '剔除系统串', dropped)


if __name__ == '__main__':
    main()
