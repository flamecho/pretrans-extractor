# -*- coding: utf-8 -*-
"""[PC-JP]月と森とあなたとわたし（LiveMaker 3, ver102）提取驱动。

与通用 `livemaker_extract.py` 的差异（本作实测变异）：
  1. ★ 本作把「剧情选项」放在**最后一个 TpWord 之后**（00000017.lsb 的
     `ジョゼを信じる/信じない`、0000000C.lsb 的 `ミントに味方する/エリアーヌに味方する`）。
     通用工具的 `limit = 最后TpWord末` 启发式会把它们当系统菜单剔除 ⇒ 本驱动用
     `limit = 脚本全长`，**按结构（選択値通道）保留所有剧情选项**，无系统菜单需要剔除。
  2. ★ 本作 PAUSE 事件密集（2355 页中约 983 个多段页），按 `dual-pause` 出
     「段行 + 整页行」双版（一次点击=一行，一页≥2次点击才出双版）。
  3. 入口链 ゲームメイン.lsb → 00000003.lsb(0文本控制脚本) → 0000000C.lsb，
     正文脚本严格线性引用 0000000C → 00000017 → 0000001A，顺序以此为准。
  4. NAMELABEL 计数 0 ⇒ 无独立名字窗，台词引号原样保留（无名牌前缀需剔除）。

判据全部结构性（类型字节/選択値标记串/引用字节序），无内容过滤、无穷举、无 OCR。
"""
import argparse
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import livemaker_extract as L

# 已实证：正文脚本严格线性引用链（refs_of 字节序）
ORDER = ['0000000C.lsb', '00000017.lsb', '0000001A.lsb']


def story_events(n, story, stats, dual_pause=True):
    b = story[n][0]
    # 必须按 dual_pause 重新扫描，否则 seg 列表为空 ⇒ 多段页判不出来
    tps = L.scan_tpwords(b, dual_pause=dual_pause)
    nchar = sum(t[3] for t in tps)
    # limit=脚本全长 ⇒ 不丢「最后一个TpWord之后」的剧情选项（本作变异）
    opts, dropped = L.scan_options(b, len(b))
    items = []
    for off, end, pages, _nc, _st in tps:
        seg_lists = _st.get('segs') or []
        for i, page_txt in enumerate(pages):
            sl = [x for x in (seg_lists[i] if i < len(seg_lists) else []) if x]
            if dual_pause and len(sl) >= 2:
                items.extend((off, 0, i * 1024 + k, x) for k, x in enumerate(sl))
                items.append((off, 0, i * 1024 + 9, page_txt))
            else:
                items.append((off, 0, i * 1024, page_txt))
    for off, txt in opts:
        items.append((off, 1, 0, txt))
    items.sort(key=lambda x: (x[0], x[1], x[2]))
    ev = [(n, v) for _o, _c, _s, v in items]
    stats[n] = {
        'lsb': len(b), 'tp': len(tps), 'nchar': nchar,
        'page': sum(t[4]['page'] for t in tps),
        'page_empty': sum(t[4]['page_empty'] for t in tps),
        'line': sum(t[4]['line'] for t in tps),
        'pause': sum(t[4]['pause'] for t in tps),
        'break_other': sum(t[4]['break_other'] for t in tps),
        'ctl': sum(t[4]['ctl'] for t in tps),
        'opt': len(opts),
        'opt_dropped': dropped,
        'mpages': sum(1 for t in tps for sl in (t[4].get('segs') or []) if len(sl) >= 2),
        'multi': sum(len(sl) for t in tps for sl in (t[4].get('segs') or []) if len(sl) >= 2),
    }
    return ev


def run(exe, out=None, dual_pause=True):
    arc = L.load(exe)
    print('VF 归档   : ver=%d, %d 项, 末项 0x%X（+6=0x%X）'
          % (arc.ver, arc.count, arc.offsets[-1], arc.offsets[-1] + 6))
    story = L.discover(arc)
    print('正文脚本  : %d 本 —— %s' % (len(story), ', '.join(sorted(story))))
    missing = [n for n in ORDER if n not in story]
    if missing:
        raise SystemExit('ORDER 中缺失脚本：%s' % missing)
    print('输出顺序  : %s' % ' → '.join(ORDER))

    stats, ev = {}, []
    for n in ORDER:
        ev.extend(story_events(n, story, stats, dual_pause))

    lines = [t for _n, t in ev]
    pg = sum(s['page'] for s in stats.values())
    pe = sum(s['page_empty'] for s in stats.values())
    op = sum(s['opt'] for s in stats.values())
    mp = sum(s['mpages'] for s in stats.values())
    ex = sum(s['multi'] for s in stats.values())

    print('--- 逐本 ---')
    for n in ORDER:
        s = stats[n]
        print('  %-14s %8d B  TpWord=%-3d 字=%-6d PAGE=%-4d LINE=%-4d PAUSE=%-3d 多段页=%-3d opt=%-2d'
              % (n, s['lsb'], s['tp'], s['nchar'], s['page'], s['line'], s['pause'],
                 s['mpages'], s['opt']))
    print('--- 合计 ---')
    print('  TpWord 块 %d ／ 正文 %d 字 ／ PAGE %d（空段 %d）／ LINE %d ／ PAUSE %d ／ 其它 %d ／ 控制符 %d'
          % (sum(s['tp'] for s in stats.values()),
             sum(s['nchar'] for s in stats.values()), pg, pe,
             sum(s['line'] for s in stats.values()),
             sum(s['pause'] for s in stats.values()),
             sum(s['break_other'] for s in stats.values()),
             sum(s['ctl'] for s in stats.values())))
    if dual_pause:
        print('  闭合（dual）：PAGE %d − 空段 %d = %d 屏；多段页 %d（一页换成「段行＋合并行」）'
              ' ⇒ %d + %d = %d 行；%d + 选项 %d = %d 行'
              % (pg, pe, pg - pe, mp, pg - pe, ex, pg - pe + ex, pg - pe + ex, op, pg - pe + ex + op))
    dr = [(n, x) for n in ORDER for x in stats[n]['opt_dropped']]
    if dr:
        print('  ⚠ 剔除的菜单项 %d 条:' % len(dr))
        for n, (off, txt, why) in dr:
            print('    %-14s 0x%06X %-24s %s' % (n, off, txt[:24], why))
    else:
        print('  剔除菜单项：0（本作无系统/标题菜单选项）')

    if out:
        body = ''.join(s + '\n' for s in lines)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'wb') as f:
            f.write(b'\xef\xbb\xbf' + body.encode('utf-8'))
        print('  写出 %s（%d B, %d 行, md5 %s）'
              % (out, os.path.getsize(out), len(lines),
                 hashlib.md5(open(out, 'rb').read()).hexdigest()))
    else:
        print('  （--verify：未写文件）')
    return stats, lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exe', required=True)
    ap.add_argument('--out')
    ap.add_argument('--single', action='store_true',
                    help='出单版（不用 dual-pause）；默认出双版')
    ap.add_argument('--verify', action='store_true')
    a = ap.parse_args()
    run(a.exe, None if a.verify else a.out, dual_pause=not a.single)


if __name__ == '__main__':
    main()
