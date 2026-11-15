#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[JP]ToucH もう一度この手が触れる世界（TVP/KiriKiri ＋ KAG3/KAGEX）全文本提取。

容器：`touch.exe` = PE（节表末 0x325400）＋ **XP3 overlay @0x326600**（508 成员）。
正文：XP3 内 `scenario/*.ks`（cp932 明文）；正文＝act1–4 / opening / ending /
      各地图事件文件（class/dote/eki/fusiki/genba/hankagai/kita/kouisitu/koumin/
      mansyon/minami/ongaku/park/rijityo/rika/taiiku/toilet）。
系统不收：mode（配置）/rclick（右键菜单）/movewin（地图移动 UI）/comwin（名字输入）/
      first/var/macro（初始化/宏）/staffroll（职员表）/ExHistoryLayer/autoInsertLabel/blur/ruby（工具）。

L0 断框（`scenario/macro.ks` 宏体 ＋ `system/MainWindow.tjs` 的 p/l 分发）：
  `[br]`     = `[l][r]` ⇒ 行クリック待ち（不 clear）＝**同框再一次点击（段）**
  `[pagebr]` = `[p][hr][label][er][skip2]` ⇒ 清屏＋点击 ＝ **框结束**
  `p` / `er` = 清屏 ⇒ 框结束；`r`＝改行合并
  `[ic …]`   = アイキャッチ（隐藏 message 层、显示「第N話／副标题」）⇒ 框结束＋上屏扉文
  `[eval exp="mes_off()"]` = 隐藏消息层 ⇒ 框结束
  `[textcross text=…]` = `[ch text=…]` 直接上屏 ⇒ 作为正文
  `waitclick` = 等点击（不换行）⇒ 段边界

双版：同一框内 ≥2 段（br/waitclick）⇒ 段行＋合并行（合并行＝同框各段拼接，确属同框）；
  跨框断引号不合并（不是同一框），只留段行并由 .allow #@open-quote 归因。

用法: python touch_text.py <scenario_dir> <out.txt>
"""
import sys, os, re, argparse

STORY = ['act1.ks', 'act2.ks', 'act3.ks', 'act4.ks', 'opening.ks', 'ending.ks',
         'class.ks', 'dote.ks', 'eki.ks', 'fusiki.ks', 'genba.ks', 'hankagai.ks',
         'kita.ks', 'kouisitu.ks', 'koumin.ks', 'mansyon.ks', 'minami.ks',
         'ongaku.ks', 'park.ks', 'rijityo.ks', 'rika.ks', 'taiiku.ks', 'toilet.ks']


def read_ks(p):
    b = open(p, 'rb').read()
    if b[:3] == b'\xef\xbb\xbf':
        return b.decode('utf-8-sig')
    return b.decode('cp932', 'replace')


def split_tags(s):
    out, i, n, buf = [], 0, len(s), ''
    while i < n:
        c = s[i]
        if c != '[':
            buf += c; i += 1; continue
        j, depth = i, 0
        while j < n:
            if s[j] == '[': depth += 1
            elif s[j] == ']':
                depth -= 1
                if depth == 0: break
            j += 1
        if j >= n:
            k = s.find(']', i + 1)
            if k < 0: break
            j = k
        if buf:
            out.append(('text', buf)); buf = ''
        inner = s[i+1:j]
        m = re.match(r'([a-zA-Z0-9_]+)', inner)
        out.append(('tag', m.group(1) if m else '', inner))
        i = j + 1
    if buf: out.append(('text', buf))
    return out


def attr(inner, name):
    m = re.search(r'%s\s*=\s*"([^"]*)"' % name, inner)
    return m.group(1) if m else None


def extract(path, stats, stop_label=None):
    t = read_ks(path).replace('\r\n', '\n').replace('\r', '\n')
    events = []
    segs, buf = [], ''
    in_script = False

    def close_seg():
        nonlocal buf
        s = buf.strip()
        if s:
            segs.append(s)
        buf = ''

    def close_box():
        nonlocal segs
        close_seg()
        if segs:
            events.append(('box', list(segs)))
            stats['boxes'] += 1
            if len(segs) > 1:
                stats['dual_boxes'] += 1
            segs = []

    for raw in t.split('\n'):
        s = raw.strip()
        if in_script:
            if s.startswith('@endscript') or s == '[endscript]':
                in_script = False
            continue
        if s.startswith('@iscript') or s == '[iscript]':
            in_script = True
            continue
        if not s or s[0] in ';*':
            if stop_label and s.startswith('*' + stop_label):
                break
            continue
        if s.startswith('@'):
            if 'mes_off' in s:
                close_box()
            continue
        for tok in split_tags(s.rstrip('\\')):
            if tok[0] == 'text':
                buf += tok[1]
                continue
            name, inner = tok[1], tok[2]
            if name in ('pagebr', 'p', 'er', 'cm', 'ct', 'endtxt', 'anten1', 'anten2'):
                close_box()
            elif name == 'ic':
                close_box()
                act = attr(inner, 'act')
                st = attr(inner, 'stitle')
                if act:
                    events.append(('top', act))
                    stats['tops'] = stats.get('tops', 0) + 1
                if st:
                    events.append(('top', st))
                    stats['tops'] = stats.get('tops', 0) + 1
            elif name in ('br', 'l', 'waitclick'):
                close_seg()
            elif name == 'textcross':
                tx = attr(inner, 'text')
                if tx:
                    buf += tx
            elif name == 'ruby2':
                # macro ruby2：基底文字在 ch 属性（text 为读音），读音不入正文
                ch = attr(inner, 'ch')
                if ch:
                    buf += ch
            elif name == 'eval':
                if 'mes_off' in inner:
                    close_box()
            # r / hr / ruby / ruby2 / nowait / endnowait 等：无文本/不断框
    close_box()

    lines = []
    for ev in events:
        if ev[0] == 'top':
            lines.append(ev[1])
            stats['top_chars'] = stats.get('top_chars', 0) + len(ev[1])
        else:
            box = ev[1]
            if len(box) == 1:
                lines.append(box[0])
                stats['seg_chars'] += len(box[0])
            else:
                lines.extend(box)
                lines.append(''.join(box))
                stats['seg_chars'] += sum(len(x) for x in box)
                stats['merged_chars'] += len(''.join(box))
    return lines


def main():
    ap = argparse.ArgumentParser(description='[JP]ToucH KiriKiri KAG3/KAGEX extractor')
    ap.add_argument('scenario')
    ap.add_argument('out')
    a = ap.parse_args()
    stats = dict(boxes=0, dual_boxes=0, lines=0, files=0,
                 seg_chars=0, merged_chars=0, top_chars=0)
    out = []
    for fn in STORY:
        p = os.path.join(a.scenario, fn)
        if not os.path.isfile(p):
            continue
        stats['files'] += 1
        # ending.ks 的 `*end` 标签之后是エンディング・スタッフロール（职员表，不收）
        out.extend(extract(p, stats, stop_label='end' if fn == 'ending.ks' else None))
    stats['lines'] = len(out)
    with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        for l in out:
            f.write(l + '\n')
    print('files=%d boxes=%d dual_boxes=%d tops=%d lines=%d seg_chars=%d merged_chars=%d top_chars=%d'
          % (stats['files'], stats['boxes'], stats['dual_boxes'], stats.get('tops', 0), stats['lines'],
             stats['seg_chars'], stats['merged_chars'], stats['top_chars']))
    print('-> ' + a.out)


if __name__ == '__main__':
    main()
