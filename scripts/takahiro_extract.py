# -*- coding: utf-8 -*-
"""takahiro_com（TyranoScript / NW.js）文本提取。

L0 判据（引擎源码 app/tyrano/plugins/kag/kag.tag.js）：
- `tag.p` = `cw:true` ＋ `flag_ref_page=true` ⇒ **点击等待＋换页（清框）** = 一框一次点击。
- `tag.l` = `cw:true`（无 flag_ref_page）⇒ **点击等待但不换页** = **同一框内多次点击** ⇒ 段行＋合并行双版。
- `tag.r` = 插入 `<br />` ⇒ 框内换行（合并）。
- `#名前` 行 = 独立名字窗（Tyrano 名札）⇒ 剔除；正文不含名。
- `[glink text="…"]` = 选项文字 ⇒ 一行一条。
"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import sys

BASE = os.path.join(VNTRANS_HOME, '_work_takahiro/app/data/scenario')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[JP]takahiro_com.txt')
FILES = ['scene1.ks', 'ekimae.ks', 'itiyaroom.ks', 'kouenn.ks',
         'ive1_nao.ks', 'ive2_mikage.ks', 'ive3_saki.ks', 'ive4_rurika.ks',
         'ive_tad.ks', 'ive_etc.ks', 'end_fri.ks', 'end_lov.ks', '_preview.ks']
TAG = re.compile(r'\[[^\]]*\]')
GLINK = re.compile(r'\[glink[^\]]*?text="([^"]*)"')


def extract_file(path, events):
    segs = []
    cur = []
    box_had_text = False

    def flush_seg():
        nonlocal cur
        t = ''.join(cur).strip()
        cur = []
        if t:
            segs.append(t)

    def flush_box():
        nonlocal segs, box_had_text
        flush_seg()
        if segs:
            events.append(('box', list(segs)))
        segs = []
        box_had_text = False

    for raw in open(path, 'rb').read().decode('utf-8-sig', 'replace').split('\n'):
        s = raw.strip()
        if not s or s.startswith((';', '@', '*')):
            continue
        if s.startswith('#'):
            continue
        if s.startswith('['):
            for m in GLINK.finditer(s):
                flush_box()
                events.append(('opt', m.group(1).strip()))
            if '[cm' in s:
                flush_box()
            continue
        for tok in re.split(r'(\[[^\]]*\])', s):
            if not tok:
                continue
            if tok.startswith('['):
                inner = tok[1:-1].strip()
                name = inner.split()[0] if inner else ''
                if name in ('p', 'l'):
                    flush_seg()
                    if name == 'p':
                        flush_box()
                elif name == 'cm':
                    flush_box()
            else:
                cur.append(tok)
    flush_box()


def main():
    events = []
    for f in FILES:
        n0 = len(events)
        extract_file(os.path.join(BASE, f), events)
        nb = sum(1 for k, v in events[n0:] if k == 'box')
        nm = sum(1 for k, v in events[n0:] if k == 'box' and len(v) >= 2)
        no = sum(1 for k, _ in events[n0:] if k == 'opt')
        print('%-16s box=%-4d multi=%-2d opt=%d' % (f, nb, nm, no))

    out = []
    for k, v in events:
        if k == 'opt':
            out.append(v)
        elif len(v) >= 2:
            out.extend(v)
            out.append(''.join(v))
        else:
            out.append(v[0])

    body = ''.join(x + '\n' for x in out)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'wb') as f:
        f.write(b'\xef\xbb\xbf' + body.encode('utf-8'))
    print('成品 %d 行 / %d 字 / %d B' % (len(out), sum(len(x) for x in out), os.path.getsize(OUT)))
    b1 = [x for x in out if '「' in x and '」' not in x]
    b2 = [x for x in out if '（' in x and '）' not in x]
    print('含「无」 %d / 含（无） %d' % (len(b1), len(b2)))
    for x in b1[:8]:
        print('  Q', x[:80])
    for x in b2[:8]:
        print('  P', x[:80])


if __name__ == '__main__':
    main()
