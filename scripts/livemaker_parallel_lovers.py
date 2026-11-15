# -*- coding: utf-8 -*-
"""[JP]Parallel Lovers 前編（LiveMaker 3）文本提取（自定义剧情顺序版）。

复用 scripts/livemaker_extract.py 的 VF 归档 / TpWord / 选项解析；
本作子剧本由控制脚本 00000001.lsb 按字节序调度，故不靠引用图，
直接从 00000001.lsb 取 5 本正文脚本的真实播放顺序后依次展开。
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import livemaker_extract as L

EXE = "_work_parallel_lovers/extracted/[JP]Parallel Lovers 前編/PL.exe"
ORCH = "00000001.lsb"          # 剧情调度器（控制脚本，0 正文）
OUT = "_work_parallel_lovers/out/[JP]Parallel Lovers 前編.txt"
STORY = ('0000001C.lsb', '00000024.lsb', '0000002D.lsb',
         '00000031.lsb', '0000004F.lsb')


def main():
    arc = L.load(EXE)
    story = L.discover(arc)
    missing = [n for n in STORY if n not in story]
    if missing:
        raise SystemExit('正文脚本缺失: ' + ', '.join(missing))

    # 从调度器按字节序取正文 5 本顺序
    b = arc.read(ORCH)
    txt = b.decode('cp932', 'replace')
    refs = [m.group(1) for m in re.finditer(r'([0-9A-Fa-f]{8}\.lsb)', txt)]
    order = []
    for r in refs:
        if r in story and r not in order:
            order.append(r)
    print('剧情顺序:', ' → '.join(order))

    stats = {}
    ev = []
    for n in order:
        ev.extend(L.story_events(n, story, {}, stats))

    lines = [t for _n, t in ev]
    # ---- 统计（仿 livemaker_extract.run 闭合校验）----
    pg = sum(s['page'] for s in stats.values())
    pe = sum(s['page_empty'] for s in stats.values())
    tp_lines = sum(len(t[2]) for n in order for t in story[n][1])
    op = sum(s['opt'] for s in stats.values())
    print('--- 逐本 ---')
    for n in order:
        s = stats[n]
        print('  %-14s %8d B  Tp=%d 字=%d PAGE=%d(空%d) LINE=%d opt=%d 行=%d'
              % (n, s['lsb'], s['tp'], s['nchar'], s['page'], s['page_empty'],
                 s['line'], s['opt'], s['lines']))
    print('  合计 PAGE %d − 空段 %d = %d，TpWord 产行 %d ⇒ %s；%d + 选项 %d = %d 行'
          % (pg, pe, pg - pe, tp_lines, 'OK' if pg - pe == tp_lines else '★不符★',
             tp_lines, op, tp_lines + op))
    dr = [(n, x) for n in order for x in stats[n]['opt_dropped']]
    if dr:
        print('  剔除菜单项 %d 条:' % len(dr))
        for n, (off, txt, why) in dr:
            print('    %-14s 0x%06X %-24s %s' % (n, off, txt[:24], why))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'wb') as f:
        f.write(b'\xef\xbb\xbf' + ''.join(s + '\n' for s in lines).encode('utf-8'))
    print('  写出 %s（%d 行，%d 字，md5 %s）'
          % (OUT, len(lines), sum(len(x) for x in lines),
             __import__('hashlib').md5(open(OUT, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main()
