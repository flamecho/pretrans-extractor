#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""マザーグースの秘密の館（PSP / 2011, Otomate）文本提取

容器：ISO → PSP_GAME/USRDIR/DATA/SCRIPT.cpk（CRI CPK）→ 965 个 KAG 风格 `.ks`（cp932, CRLF）

脚本语法（L0）：
  [message window="kyara" name="name_art.tga" voice="..."]
  \t正文行（行内 tab 起头；一框多行＝软换行）
  [/message]
  ⇒ 一个 [message] 块 = 一次点击；块内多行合并为一行。
  名字是**图片**（name="name_*.tga"）⇒ 无文本名札，正文里不加说话人。
  [f size=".."]/[/f] 为字体强调标记，剥掉；[firstname] 为主角名宏。
"""
import os
import re
import sys

BLOCK = re.compile(r'\[message([^\]]*)\](.*?)\[/message\]', re.S)
TAG = re.compile(r'\[f(?:\s[^\]]*)?\]|\[/f\]')
SKIP = {'test.ks'}


def extract(path, hero):
    raw = open(path, 'rb').read()
    d = raw.decode('cp932', 'replace')
    out = []
    for m in BLOCK.finditer(d):
        body = m.group(2)
        parts = [ln.strip() for ln in body.replace('\r', '\n').split('\n')]
        parts = [p for p in parts if p]
        t = ''.join(parts)
        t = TAG.sub('', t).replace('[firstname]', hero).strip()
        if t:
            out.append(t)
    return out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    hero = sys.argv[3] if len(sys.argv) > 3 else '名前'
    out, nf = [], 0
    for n in sorted(os.listdir(src)):
        if not n.endswith('.ks') or n in SKIP:
            continue
        ls = extract(os.path.join(src, n), hero)
        if ls:
            nf += 1
            out.extend(ls)
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(out) + '\n')
    print('files', nf, 'lines', len(out), '->', dst)


if __name__ == '__main__':
    main()
