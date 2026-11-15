#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[JP]Tether（KiriKiri / TVP(KiriKiri) KAG3）全文本提取。

容器：`Tether.exe` = PE（节表末 0x32A800）＋ **XP3 overlay @0x32BA00**（XP3 ver，146 成员）；
      `wuvorbis.dll` 为 KAG Ogg 插件 ⇒ 引擎 TVP(KiriKiri)。
正文：XP3 内 `scenario/*.ks`（cp932 明文 KAG3）；正文文件＝honpen / honpen_c / honpen_m /
      aremaru（おまけ） / atogaki（あとがき）。其余为系统菜单/画廊/音量 UI/工具脚本。

L0 断框（`system/MainWindow.tjs` / `MessageLayer.tjs` 的 tag 分发）：
  p / endtxt = showPageBreak（清屏＋等点击）⇒ 一次点击、文本框结束（一行）
  l          = showLineBreak（等点击、不清屏）⇒ **同一文本框内再一次点击（段边界）**
  r / hr     = 改行（无点击）⇒ 框内排版换行，合并
  cm / ct / er = 清消息层 ⇒ 框结束
  `[e]`      = first.ks 宏 `@p @label @cm` ⇒ 框结束（等价 p+cm）
  `@cm`      = @ 指令清层 ⇒ 框结束
双版（用户规则）：同一框内 [l] ≥2 ⇒ 段行＋合并行（合并行＝同框各段拼接，确属同框）；
  跨「框」断引号**不合并**（不是同一框），只留段行并由 .allow #@open-quote 归因。

用法: python tether_text.py <scenario_dir> <out.txt>
"""
import sys, os, re, argparse

FILES = ['honpen.ks', 'honpen_c.ks', 'honpen_m.ks', 'aremaru.ks', 'atogaki.ks']
SYS_NAV = {'閉じる', '戻る', '●戻る', '開始する', 'エンディングリスト',
           'あとがき（おまけ付き）', '終了する', 'ＯＫ', '●ＴｅｔｈｅｒＺＥＲＯの世界へ飛ぶ',
           '●鍵を入れなおす'}


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
        name = m.group(1) if m else ''
        out.append(('tag', name, inner))
        i = j + 1
    if buf: out.append(('text', buf))
    return out


def extract(path, stats):
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
            continue
        if s.startswith('@'):
            low = s.lower()
            if re.match(r'@current\s+layer\s*=', low) or re.match(r'@layopt', low):
                # 层切换/可见性：不同层不属正文框；隐藏 message0 ⇒ 框结束
                if 'layer=message0' in low and ('visible=false' in low):
                    close_box()
                continue
            if re.match(r'@cm\b', low) or re.match(r'@tugi\b', low):
                close_box(); continue
            # 其它 @ 指令：无文本
            continue
        if '[link' in s:
            if segs or buf.strip():
                close_box()
            pos = s.find('[link')
            while pos >= 0:
                j = s.find(']', pos)
                k = s.find('[endlink', j + 1)
                if j < 0 or k < 0:
                    break
                txt = s[j+1:k]
                txt = ''.join(x[1] for x in split_tags(txt) if x[0] == 'text').strip()
                if txt and txt not in SYS_NAV:
                    events.append(('opt', txt))
                    stats['opts'] += 1
                pos = s.find('[link', k + 1)
            continue
        for tok in split_tags(s.rstrip('\\')):
            if tok[0] == 'text':
                buf += tok[1]
                continue
            name, inner = tok[1], tok[2]
            if name in ('endtxt', 'p', 'e', 'cm', 'ct', 'er', 'tugi', 'cred', 'cl'):
                close_box()
            elif name == 'l':
                close_seg()
            elif name == 'emb':
                m = re.match(r'emb\s+exp\s*=\s*(.*)', inner, re.S)
                if m:
                    v = m.group(1).strip().strip('"\'')
                    if re.fullmatch(r'[\u3040-\u30ff\u4e00-\u9fff_a-zA-Z0-9.]+', v):
                        buf += v
            # r/hr/ruby 等：无文本、不断框
    close_box()

    lines = []
    for ev in events:
        if ev[0] == 'opt':
            lines.append(ev[1])
            stats['opt_chars'] = stats.get('opt_chars', 0) + len(ev[1])
        else:
            box = ev[1]
            if len(box) == 1:
                lines.append(box[0])
                stats['seg_chars'] = stats.get('seg_chars', 0) + len(box[0])
            else:
                lines.extend(box)
                lines.append(''.join(box))
                stats['seg_chars'] = stats.get('seg_chars', 0) + sum(len(x) for x in box)
                stats['merged_chars'] = stats.get('merged_chars', 0) + len(''.join(box))
    return lines


def main():
    ap = argparse.ArgumentParser(description='[JP]Tether KiriKiri KAG3 extractor')
    ap.add_argument('scenario')
    ap.add_argument('out')
    a = ap.parse_args()
    stats = dict(boxes=0, dual_boxes=0, opts=0, lines=0, files=0, seg_chars=0, merged_chars=0, opt_chars=0)
    out = []
    for fn in FILES:
        p = os.path.join(a.scenario, fn)
        if not os.path.isfile(p):
            continue
        stats['files'] += 1
        out.extend(extract(p, stats))
    stats['lines'] = len(out)
    with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        for l in out:
            f.write(l + '\n')
    print('files=%d boxes=%d dual_boxes=%d opts=%d lines=%d seg_chars=%d merged_chars=%d opt_chars=%d'
          % (stats['files'], stats['boxes'], stats['dual_boxes'], stats['opts'], stats['lines'],
             stats['seg_chars'], stats['merged_chars'], stats['opt_chars']))
    print('-> ' + a.out)


if __name__ == '__main__':
    main()
