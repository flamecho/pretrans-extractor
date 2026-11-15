#!/usr/bin/env python3
"""[JP]Sugar（LiveMaker 3 / 野良猫企画 2016）文本提取驱动。

复用 scripts/livemaker_extract.py 的底层（VF 归档 ＋ LMScript .lsb ＋ LiveNovel TpWord），
但本驱动自己组装输出，避免共享 OPT_SKIP 对 `00000001.lsb` 名的碰撞（那是 [JP]Limit 的区段）。

判据（结构性，全部来自引擎文档 livemaker-lsb.md）：
  - 正文只在 `00000001.lsb`（单一主脚本）。排除：
      * '00000001 (n-PC の競合コピー 2016-08-03).lsb' —— 同步冲突副本：
        0 引用、95.3% 页与正篇逐字相同、早于最终版(2016-11-07) ⇒ 死数据。
      * '00000081.lsb' —— `スタッフロール`（系统 UI，1 行）。
  - 名札印在正文框内（NAMELABEL=0、【】1082 处）⇒ 保留同行、品检 --inline-name。
  - 无 TWdImg/TWdOpeVar（glyph 普查 0）⇒ 不需 --inline-placeholder。
  - PAUSE=50 ⇒ --dual-pause（一框多次点击＝同框继续；段行＋合并行，合并行确属同框）。
  - 选项 30（To(____N)=Str + 選択値 结构；0 系统菜单剔除）。

用法：
    python scripts/livemaker_sugar.py --verify
    python scripts/livemaker_sugar.py --out "提取结果/<名>.txt"
    python scripts/livemaker_sugar.py --exe "<内层 exe>" --out ...
"""
import sys
import os
import hashlib
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import livemaker_extract as L

EXE_DEFAULT = "_work_sugar/[JP]Sugar/Sugar.exe"
ROOT = '00000001.lsb'
EXCLUDE = [
    '00000001 (n-PC の競合コピー 2016-08-03).lsb',
    '00000081.lsb',
]


def extract_story(arc, name, dual_pause, skip=()):
    b = arc.read(name)
    tps = L.scan_tpwords(b, dual_pause=dual_pause)
    limit = tps[-1][1] if tps else 0
    opts, dropped = L.scan_options(b, limit, skip)
    items = []
    for off, end, pages, _nc, st in tps:
        if dual_pause:
            seg_lists = st.get('segs') or []
            for i, page_txt in enumerate(pages):
                sl = [x for x in (seg_lists[i] if i < len(seg_lists) else []) if x]
                if len(sl) >= 2:                      # 一页 ≥2 次点击 ⇒ 段行 ＋ 合并行
                    items.extend((off, 0, i * 1024 + k, x) for k, x in enumerate(sl))
                    items.append((off, 0, i * 1024 + 9, page_txt))
                else:
                    items.append((off, 0, i * 1024, page_txt))
        else:
            for s in pages:
                items.append((off, 0, 0, s))
    for off, txt in opts:
        items.append((off, 1, 0, txt))
    items.sort(key=lambda x: (x[0], x[1], x[2]))
    ev = [(name, val) for _o, _c, _s, val in items]
    return ev, opts, dropped, tps


def main():
    ap = argparse.ArgumentParser(description='[JP]Sugar (LiveMaker 3) 文本提取')
    ap.add_argument('--exe', default=EXE_DEFAULT)
    ap.add_argument('--out')
    ap.add_argument('--single', action='store_true',
                    help='出单版（不做 PAUSE 双版，仅用于对照）')
    ap.add_argument('--verify', action='store_true')
    a = ap.parse_args()

    arc = L.load(a.exe)
    story = L.discover(arc)
    for n in EXCLUDE:
        story.pop(n, None)
    if ROOT not in story:
        sys.exit('root %s 不在 story（请检查 VF）' % ROOT)

    dual = not a.single
    ev, opts, dropped, tps = extract_story(arc, ROOT, dual)
    lines = [t for _n, t in ev]

    pg = sum(t[4]['page'] for t in tps)
    pe = sum(t[4]['page_empty'] for t in tps)
    ln = sum(t[4]['line'] for t in tps)
    pa = sum(t[4]['pause'] for t in tps)
    # dual 段增量：Σ(len(sl)) over 多段页
    ex = sum(len(sl) for t in tps for sl in (t[4].get('segs') or []) if len(sl) >= 2) if dual else 0
    op = len(opts)

    print('=== [JP]Sugar 提取（%s）===' % ('双版 dual-pause' if dual else '单版'))
    print('  保留正文脚本: %s' % ROOT)
    print('  排除(死数据/系统UI): %s' % ', '.join(EXCLUDE))
    print('  VF ver=%d, %d 项；TpWord=%d 块；字=%d'
          % (arc.ver, arc.count, len(tps), sum(t[3] for t in tps)))
    print('  PAGE=%d 空段=%d LINE=%d PAUSE=%d' % (pg, pe, ln, pa))
    print('  选项=%d（剔除系统菜单 %d）' % (op, len(dropped)))
    if dual:
        print('  闭合(dual): PAGE %d − 空段 %d = %d 屏；段增量 %d；+ 选项 %d = %d 行'
              % (pg, pe, pg - pe, ex, op, pg - pe + ex + op))
        print('  产出行数 = %d（应 = 上式）' % len(lines))
    else:
        print('  闭合(单版): PAGE %d − 空段 %d = %d；+ 选项 %d = %d 行'
              % (pg, pe, pg - pe, op, pg - pe + op))
        print('  产出行数 = %d（应 = 上式）' % len(lines))
    if dropped:
        print('  剔除菜单项:')
        for off, txt, why in dropped:
            print('    0x%06X %-20s %s' % (off, txt[:20], why))

    if a.out and not a.verify:
        body = ''.join(x + '\n' for x in lines)
        os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
        with open(a.out, 'wb') as f:
            f.write(b'\xef\xbb\xbf' + body.encode('utf-8'))
        print('  写出 %s (%d B, md5 %s)'
              % (a.out, os.path.getsize(a.out), hashlib.md5(open(a.out, 'rb').read()).hexdigest()))
    else:
        print('  （--verify：未写文件）')


if __name__ == '__main__':
    main()
