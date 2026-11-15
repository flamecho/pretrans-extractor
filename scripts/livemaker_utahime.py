# -*- coding: utf-8 -*-
"""[PC-JP]歌姫と王様（LiveMaker 3 / VF ver=102）文本提取。

复用 scripts/livemaker_extract.py 的 VF / TpWord / 选项解析。本作要点：

1. ★ 入口链穿控制脚本：`ゲームメイン.lsb` → `00000001.lsb`（标题菜单，0 正文）
   → `00000015.lsb`（正文）。工具默认 `build_order` 只看入口的直接引用，找不到
   正文根 ⇒ 这里按入口链 + 引用点**显式**给顺序。
2. ★ 正文脚本 10 本（判据＝TpWord 字数>0）：
   15 → 2D → 14A → 197 → 1D6 → 20D → {2E0(クラウ), 2E4(ガート), 2E2(ラビ)} 、
   2E0/2E4/2E2/347 由 20D 末段按字节序引用（347＝无路线/bad end）。
3. ★ 排除 483/485/487：三本由 `00000481.lsb`（回想モード菜单）引用，
   选项字面为 `クラウ回想１〜１０` 等，且其全部页与 2E0/2E4/2E2 **逐页相同**
   （483 566/566、485 637/639、487 891/893）⇒ 回想载体重放，非新正文。
4. ★ 一框多次点击：6 个页面在页内出现 `{PAUSE}`（`\x01PAUSE`）
   ⇒ 段行 ＋ 合并行双版（`--dual-pause` 语义）。
5. ★ 主角名是变量 `主役の名前`（2,355 处）；默认名由 `文字列入力` 调用参数
   给出：`デフォルト名：ルーシー,1,8,主役の名前` ⇒ 用默认名 `ルーシー` 替换。
6. ★ 消息对话框（名前确认 / OP 跳过）的提示 TpWord 块在字节序上晚于其
   `はい/いいえ` 按钮记录；若某脚本的**所有 1 页 TpWord 块都恰有前邻 2 条选项**
   （＝整本都是对话框结构，本作仅 00000015.lsb），把这些按钮排到提示之后。
"""
import hashlib
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
import livemaker_extract as L

EXE = os.path.join(VNTRANS_HOME, '_work_utahime/src/歌姫と王様/歌姫と王様.exe')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[PC-JP]歌姫と王様.txt')
STORY = ['00000015.lsb', '0000002D.lsb', '0000014A.lsb', '00000197.lsb',
         '000001D6.lsb', '0000020D.lsb', '000002E0.lsb', '000002E4.lsb',
         '000002E2.lsb', '00000347.lsb']
REPLAY = ['00000483.lsb', '00000485.lsb', '00000487.lsb']
DEFAULT_NAME = 'ルーシー'
VAR_TOKEN = '\u27e6VAR:%s\u27e7' % '主役の名前'


def is_dialog_script(tps, opts):
    """整本脚本是否都是「1 页 TpWord ＋ 前邻 2 条按钮」的对话框结构。"""
    ones = [i for i, t in enumerate(tps) if len(t[2]) == 1]
    if not ones:
        return False
    for i in ones:
        prev = tps[i - 1][1] if i else 0
        if len([q for q, _t in opts if prev <= q < tps[i][0]]) != 2:
            return False
    return True


def emit(name, story, stats):
    b, tps, nchar = story[name]
    opts, dropped = L.scan_options(b, tps[-1][1] if tps else 0, L.OPT_SKIP.get(name, ()))
    dialog = is_dialog_script(tps, opts)
    if dialog:
        print('  %s：对话框脚本（全部 1 页块各前邻 2 按钮）⇒ 提示排按钮前' % name)
    btn_order = {}
    if dialog:
        for bi, (hoff, _e, hpages, _n, _s) in enumerate(tps):
            if len(hpages) != 1:
                continue
            prev = tps[bi - 1][1] if bi else 0
            qs = sorted(q for q, _t in opts if prev <= q < hoff)[:2]
            for k, q in enumerate(qs):
                btn_order[q] = (hoff, 1 + k)

    items = []
    for bi, (off, _end, pages, _nc, st) in enumerate(tps):
        seg_lists = st.get('segs') or []
        if L.DUAL_PAUSE:
            for i, page_txt in enumerate(pages):
                sl = [x for x in (seg_lists[i] if i < len(seg_lists) else []) if x]
                if len(sl) >= 2:
                    items.extend((off, i * 32 + k, x) for k, x in enumerate(sl))
                    items.append((off, i * 32 + 20, page_txt))
                else:
                    items.append((off, i * 32, page_txt))
            continue
        for s in pages:
            items.append((off, 0, s))

    for q, txt in opts:
        if q in btn_order:
            items.append((btn_order[q][0], btn_order[q][1], txt))
            continue
        items.append((q, 1, txt))
    items.sort(key=lambda x: (x[0], x[1]))

    ev = [(name, val) for _o, _k, val in items]

    st_sum = {
        'lsb': len(b), 'tp': len(tps), 'nchar': nchar,
        'page': sum(t[4]['page'] for t in tps),
        'page_empty': sum(t[4]['page_empty'] for t in tps),
        'line': sum(t[4]['line'] for t in tps),
        'pause': sum(t[4]['pause'] for t in tps),
        'break_other': sum(t[4]['break_other'] for t in tps),
        'ctl': sum(t[4]['ctl'] for t in tps),
        'opt': len(opts), 'opt_dropped': dropped,
        'multi': sum(len(sl) for t in tps for sl in (t[4].get('segs') or []) if len(sl) >= 2)
                 if L.DUAL_PAUSE else 0,
        'mpages': sum(1 for t in tps for sl in (t[4].get('segs') or []) if len(sl) >= 2)
                  if L.DUAL_PAUSE else 0,
        'lines': len(ev),
    }
    stats[name] = st_sum
    return ev


def main():
    L.DUAL_PAUSE = True
    L.INLINE_PH = True
    arc = L.load(EXE)
    story = L.discover(arc)
    missing = [n for n in STORY if n not in story]
    if missing:
        raise SystemExit('正文脚本缺失: ' + ', '.join(missing))

    for r in REPLAY:
        if r not in story:
            continue
        rp = [p for t in story[r][1] for p in t[2]]
        base = max(STORY, key=lambda m: sum(1 for p in rp if p in set(
            x for t in story[m][1] for x in t[2])))
        hit = sum(1 for p in rp if p in set(x for t in story[base][1] for x in t[2]))
        print('  排除 %s：页 %d，与 %s 同页 %d ⇒ 回想重放' % (r, len(rp), base, hit))

    stats, ev = {}, []
    for n in STORY:
        ev.extend(emit(n, story, stats))

    lines = [t.replace(VAR_TOKEN, DEFAULT_NAME) for _n, t in ev]
    body = ''.join(s + '\n' for s in lines)

    pg = sum(s['page'] for s in stats.values())
    pe = sum(s['page_empty'] for s in stats.values())
    pa = sum(s['pause'] for s in stats.values())
    mp = sum(s['mpages'] for s in stats.values())
    multi = sum(s['multi'] for s in stats.values())
    op = sum(s['opt'] for s in stats.values())
    print('--- 逐本 ---')
    for n in STORY:
        s = stats[n]
        print('  %-14s %8d B  TpWord=%-3d 字=%-6d PAGE=%-4d(空%d) LINE=%-4d PAUSE=%-2d 多段页=%-2d opt=%-2d 行=%-4d'
              % (n, s['lsb'], s['tp'], s['nchar'], s['page'], s['page_empty'],
                 s['line'], s['pause'], s['mpages'], s['opt'], s['lines']))
    print('--- 合计 ---')
    print('  TpWord %d 块 / 正文 %d 字 / PAGE %d（空段 %d）/ LINE %d / PAUSE %d / 其它 break %d / 控制符 %d'
          % (sum(s['tp'] for s in stats.values()),
             sum(s['nchar'] for s in stats.values()), pg, pe,
             sum(s['line'] for s in stats.values()), pa,
             sum(s['break_other'] for s in stats.values()),
             sum(s['ctl'] for s in stats.values())))
    print('  闭合：%d − %d = %d 屏；多段页 %d ⇒ +%d；%d + 选项 %d = %d 行'
          % (pg, pe, pg - pe, mp, multi, pg - pe + multi, op, pg - pe + multi + op))
    print('  成品 %d 行 / %d 字（主角名变量 %d 处 ⇒ %s）'
          % (len(lines), sum(len(x) for x in lines), body.count(DEFAULT_NAME), DEFAULT_NAME))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'wb') as f:
        f.write(b'\xef\xbb\xbf' + body.encode('utf-8'))
    print('  写出 %s（%d B, md5 %s）'
          % (OUT, os.path.getsize(OUT), hashlib.md5(open(OUT, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main()
