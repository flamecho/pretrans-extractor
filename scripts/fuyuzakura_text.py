#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[PC-JP]冬桜抄 -さくらがたり-（KiriKiri KAG3 · data.xp3）全文本提取。

L0 判据（system/MainWindow.tjs 的 tag handler 表，引擎代码级）：
  p  = showPageBreak   清屏 + 等点击 ⇒ 一次点击、文本框结束（endtxt 宏体 = [p][r][cm]）
  l  = showLineBreak   等点击但不清屏 ⇒ 同一文本框内再一次点击（段边界）
  r  = 改行（无点击）               ⇒ 框内排版换行，合并进同一行
  cm/ct/er = 清消息层（endtxt 中 cm 在 p 之后）
  名字 = @【X】 宏（macro.ks），宏体 [nowait]【<名>】[r][endnowait] 写入 message0
        ⇒ 名札在正文文本框内 ⇒ 保留并接在同行台词前（--inline-name 口径）。
  f.defname1=五条 / f.defname2=咲 / f.kooniName=若葉（first.ks 初始化）⇒ emb 变量按默认名回填。
  姓名输入 UI 在 @current layer=message2（10510.ks / first.ks）⇒ 非 message0 正文，不计。

双版：用户规则「一框多次点击或一次点击多框 ⇒ 出双版」。本作 [l] 共 10 处（4 个框）
  为框内多次点击 ⇒ 这些框输出「段行＋合并行」；其余框单段 ⇒ 只出一行（不重复）。

用法:
  python fuyuzakura_text.py <scenario_dir> <out.txt>
  （scenario_dir = 解包后的 xp3data/scenario，内含 01..08 章目录）
"""
import sys, os, re, glob, argparse

PROTAG = '咲'
FNAME = '五条'
KOONI = '若葉'

NAME_DEFAULT = {
    '咲': PROTAG, '子真人': '子真人', '真人': '真人', '吹雪': '吹雪',
    '垂氷': '垂氷', '陽向': '陽向', '霧島': '霧島', '仔鬼': KOONI,
    '祖母': '祖母',
}

EXCLUDE = {'macro.ks', 'first.ks', 'link.ks'}


def read_ks(p):
    b = open(p, 'rb').read()
    if b[:2] == b'\xff\xfe':
        return b.decode('utf-16')
    if b[:3] == b'\xef\xbb\xbf':
        return b.decode('utf-8-sig')
    if b.count(0) > len(b) * 0.25:
        return b.decode('utf-16-le', 'replace')
    return b.decode('cp932', 'replace')


def split_tags(s):
    """行 → [('text', s) / ('tag', name, inner)]；处理 %[...] 嵌套。"""
    out, i, n, buf = [], 0, len(s), ''
    while i < n:
        c = s[i]
        if c != '[':
            buf += c; i += 1; continue
        j, depth = i, 0
        while j < n:
            if s[j] == '[':
                depth += 1
            elif s[j] == ']':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if j >= n:
            k = s.find(']', i + 1)
            if k < 0:
                break
            j = k
        if buf:
            out.append(('text', buf)); buf = ''
        inner = s[i + 1:j]
        m = re.match(r'([^\[\]\s=]+)', inner)
        out.append(('tag', m.group(1) if m else '', inner))
        i = j + 1
    if buf:
        out.append(('text', buf))
    return out


def emb_value(exp):
    exp = exp.strip().strip('"\'')
    m = re.search(r"f\.tmpname\s*=\s*['\"]([^'\"]*)['\"]", exp)
    if m:
        return m.group(1)
    if exp.endswith('f.Fname'):
        return FNAME
    if exp.endswith('f.name'):
        return PROTAG
    if exp.endswith('f.kooniName'):
        return KOONI
    return None


def macro_display_name(inner_name, attrs):
    """@【X】 宏调用 → 显示名。"""
    m = re.search(r'name\s*=\s*"([^"]*)"', attrs) or re.search(r'name\s*=\s*([^\s]+)', attrs)
    if m:
        val = m.group(1)
        got = emb_value(val)
        if got:
            return got
        m2 = re.search(r"['\"]([^'\"]+)['\"]", val)
        if m2:
            lit = m2.group(1)
            g2 = emb_value(lit)
            return g2 if g2 else lit
        return None
    return NAME_DEFAULT.get(inner_name)


def extract_file(path, stats=None):
    """返回该文件的输出行（框=一行；多点击框=段行+合并行；选项一行一条）。"""
    t = read_ks(path)
    events = []
    segs, buf = [], ''
    layer = 'message0'

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
            if stats is not None:
                stats['boxes'] += 1
                if len(segs) > 1:
                    stats['dual_boxes'] += 1
            segs = []

    in_script = False
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
            m = re.match(r'@current\s+layer\s*=\s*(\w+)', s)
            if m:
                layer = m.group(1)
                continue
            m = re.match(r'@【([^】]+)】', s)
            if m and layer == 'message0':
                disp = macro_display_name(m.group(1), s[m.end():])
                if disp:
                    pref = '【%s】' % disp
                    # 同一角色多条件名札（cond= 语音变体）→ 只保留一个
                    if re.fullmatch(r'【[^】]*】', buf.strip()):
                        buf = pref
                    else:
                        buf += pref
            continue
        if '[link' in s:
            # 选项行：[link ...]文本[endlink][r] ⇒ 只取选项文字
            if segs or buf.strip():
                close_box()
            pos = s.find('[link')
            while pos >= 0:
                j = s.find(']', pos)
                k = s.find('[endlink', j + 1)
                if j < 0 or k < 0:
                    break
                txt = s[j + 1:k]
                txt = ''.join(t2[1] for t2 in split_tags(txt) if t2[0] == 'text').strip()
                if txt:
                    events.append(('opt', txt))
                    if stats is not None:
                        stats['opts'] += 1
                pos = s.find('[link', k + 1)
            continue
        for tok in split_tags(s):
            if tok[0] == 'text':
                if layer == 'message0':
                    buf += tok[1]
                continue
            name, inner = tok[1], tok[2]
            if name in ('endtxt', 'p'):
                close_box()
            elif name == 'l':
                close_seg()
            elif name in ('cm', 'ct', 'er'):
                close_box()
            elif name == 'emb':
                if layer == 'message0':
                    m = re.match(r'emb\s+exp\s*=\s*(.*)', inner, re.S)
                    if m:
                        got = emb_value(m.group(1))
                        buf += got if got else ''
            # r/hr 及控制标签：无文本、不断框
    close_box()

    # ★ 跨框断引号＝「一次点击多框」（skill S6-lines-dual.md §0.4）：
    #   前框开「/『 未收、紧邻后框正好收尾 ⇒ 两框为同一句 ⇒ 段行＋合并行。
    def qdel(t):
        return (t.count('「') - t.count('」'), t.count('『') - t.count('』'))

    merged_events = []
    i = 0
    while i < len(events):
        ev = events[i]
        if ev[0] == 'box' and i + 1 < len(events) and events[i + 1][0] == 'box':
            t1, t2 = ''.join(ev[1]), ''.join(events[i + 1][1])
            d1, d2 = qdel(t1), qdel(t2)
            for a, b in ((d1[0], d2[0]), (d1[1], d2[1])):
                if a > 0 and b < 0 and a + b == 0 and d1[0] + d2[0] == 0 and d1[1] + d2[1] == 0:
                    merged_events.append(('group', ev[1] + events[i + 1][1]))
                    if stats is not None:
                        stats['cross_groups'] = stats.get('cross_groups', 0) + 1
                    i += 2
                    break
            else:
                merged_events.append(ev)
                i += 1
            continue
        merged_events.append(ev)
        i += 1

    lines = []
    for ev in merged_events:
        if ev[0] == 'opt':
            lines.append(ev[1])
        else:
            box = ev[1]
            if len(box) == 1:
                lines.append(box[0])
            else:
                lines.extend(box)
                lines.append(''.join(box))
    return lines


def main():
    ap = argparse.ArgumentParser(description='[PC-JP]冬桜抄 -さくらがたり- KiriKiri KAG3 text extractor')
    ap.add_argument('scenario', help='解包后的 xp3data/scenario 目录')
    ap.add_argument('out', help='输出 txt（UTF-8 BOM / LF）')
    args = ap.parse_args()

    files = []
    for ch in sorted(glob.glob(os.path.join(args.scenario, '0*'))):
        if not os.path.isdir(ch):
            continue
        for f in sorted(glob.glob(os.path.join(ch, '*.ks'))):
            if os.path.basename(f) not in EXCLUDE:
                files.append(f)

    stats = dict(files=len(files), boxes=0, opts=0, dual_boxes=0, lines=0)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, 'w', encoding='utf-8-sig', newline='\n') as fh:
        for f in files:
            for l in extract_file(f, stats):
                fh.write(l + '\n')
                stats['lines'] += 1
    print(stats, '->', os.path.abspath(args.out))


if __name__ == '__main__':
    main()
