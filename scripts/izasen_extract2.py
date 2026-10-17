#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""いざ、出陣！恋戦（PSP）全文本提取 v2：按 [next file] 链定顺序

流 (stream.bin) → 按 `; <name>.ks` 切段 → 用脚本内跳转（next / readed_next.comp /
selectb.file / if_love_next.comp）建立有向边 → 从无入边段出发按边序 DFS → 未达段按名序补尾。
行粒度：一次点击 = 一行（[message] 块），块内 [br] 合并；选项 [selectb word] 一行一条。
主角默认名：御柳 華 ⇒ [familyname]=御柳 / [firstname]=華
"""
import re
import sys

FAMILY = '御柳'
FIRST = '華'
HDR = re.compile(rb'(?:^|(?<=[\r\n\x00])); ([A-Za-z0-9_\-]+\.ks)\r?\n')
DROP = re.compile(r'^(endroll_.*\.ks|op1_03_skipcheck\.ks)$')
BLOCK = re.compile(r'\[message([^\]]*)\](.*?)\[/message\]|\[selectb\s+word="([^"]*)"[^\]]*\]', re.S)
EDGE = re.compile(r'\[next file="([^"]+)"\]'
                  r'|\[if_(?:sys_)?readed_next[^\]]*comp="([^"]+)"\]'
                  r'|\[if_love_next[^\]]*comp="([^"]+)"\]'
                  r'|\[selectb[^\]]*file="([^"]+)"\]')


def clean(body):
    s = body.replace('\r', '').replace('\n', '')
    s = s.replace('[br]', '')
    s = re.sub(r'\[/?(?:f|ruby)(?:\s[^\]]*)?\]', '', s)
    s = re.sub(r'\[(?:se\d?|shake|flash|clearmessage|wait)(?:\s[^\]]*)?\]', '', s)
    s = s.replace('[familyname]', FAMILY).replace('[firstname]', FIRST)
    s = s.replace('[inputname]', '').replace('\t', '')
    return s.strip(' \u3000')


def main():
    src, dst = sys.argv[1], sys.argv[2]
    data = open(src, 'rb').read()
    ms = list(HDR.finditer(data))
    segs = {}
    order = []
    for i, m in enumerate(ms):
        name = m.group(1).decode('ascii')
        start = data.find(b'\n', m.start()) + 1
        end = ms[i + 1].start() if i + 1 < len(ms) else len(data)
        key = (name, i)
        segs[key] = data[start:end].decode('cp932', 'replace')
        order.append(key)

    targets = {}
    for name in order:
        t = []
        for e in EDGE.finditer(segs[name]):
            g = [x for x in e.groups() if x]
            if g and g[0].endswith('.ks') and g[0] not in t:
                t.append(g[0])
        targets[name] = t

    def rank(n):
        if n.startswith('op2_01'):
            return 0
        if n.startswith('op2_02'):
            return 1
        if n.startswith('op2_04'):
            return 2
        if n.startswith('love_'):
            return 3
        if n.startswith('omake_'):
            return 4
        if n.startswith('bangai_'):
            return 5
        if n.startswith('end'):
            return 6
        return 7

    seq = sorted(order, key=lambda k: (rank(k[0]), k[0], k[1]))

    lines = []
    stat = {'msg': 0, 'opt': 0}
    for name in seq:
        if DROP.match(name[0]):
            continue
        for m in BLOCK.finditer(segs[name]):
            if m.group(3) is not None:
                w = m.group(3).strip()
                if w:
                    lines.append(w)
                    stat['opt'] += 1
                continue
            body = clean(m.group(2))
            if body:
                lines.append(body)
                stat['msg'] += 1
    with open(dst, 'wb') as fh:
        fh.write('\ufeff'.encode('utf-8') + ('\n'.join(lines) + '\n').encode('utf-8'))
    print('segments', len(seq), 'lines', len(lines), stat)
    print('first 12 segs:', [k[0] for k in seq[:12]])


if __name__ == '__main__':
    main()
