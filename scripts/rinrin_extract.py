# -*- coding: utf-8 -*-
"""[PC-JP]凜々蝶さまのおっしゃる通り！（KiriKiri / data.xp3 / cp932 平文 KAG3）文本提取。

L0 判据：
- `[plc]` 宏定义（scenario/マクロ.ks）= `[l]`＋`[label]`＋`[ct]` ⇒ 一次点击、一框、随后清字。
- 原生 `[p]` = 改页（一次点击换框）。
- 原生 `[l]` = 同行内「クリック待ち」⇒ 同一框内多次点击 ⇒ 段行＋合并行双版。
- `[ct]/[er]/[cm]` = 清字/清层；缓冲非空时结框。
- 注释 `;` 整行丢弃；`@` 命令行丢弃；标签一律剥除。
- 主角名变量 `[emb exp="sf.名前"]` ⇒ 默认名 `凜々蝶`（`オープニング.ks` 的 `[eval exp="sf.名前='凜々蝶'"]`）。
- `[選択肢 target=…] 文字 [選択済み]` ⇒ 选项一行一条。
"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
from xp3 import XP3

XP3PATH = os.path.join(VNTRANS_HOME, '_work_rinrin/src/[PC-JP]凜々蝶さまのおっしゃる通り！/data.xp3')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[PC-JP]凜々蝶さまのおっしゃる通り！.txt')
DEFAULT_NAME = '凜々蝶'
SKIP_FROM_LABEL = {'オープニング.ks': '体験版終了'}
FILES = ['オープニング.ks', '休むイベント.ks', '友好イベント.ks',
         '好感イベント.ks', '愛情イベント.ks', '追加エピソード.ks', 'おまけ.ks']


def scan_tags(line):
    """把一行拆成 [(is_tag, text)]，标签支持引号内 ] 与嵌套方括号。"""
    out, i, n = [], 0, len(line)
    buf = []
    while i < n:
        c = line[i]
        if c == '[':
            if buf:
                out.append(('t', ''.join(buf))); buf = []
            j, depth, q = i + 1, 1, None
            while j < n:
                ch = line[j]
                if q:
                    if ch == q:
                        q = None
                elif ch in '"\'':
                    q = ch
                elif ch == '[':
                    depth += 1
                elif ch == ']':
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            out.append(('tag', line[i + 1:j]))
            i = j + 1
        else:
            buf.append(c); i += 1
    if buf:
        out.append(('t', ''.join(buf)))
    return out


def tag_name(tag):
    m = re.match(r'([^\s\]=]+)', tag.strip())
    return m.group(1) if m else ''


def extract(name, raw):
    lines = raw.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    boxes = []           # [(segments list)]
    segs = []            # current box segments
    cur = []             # current segment text
    in_option = False
    opt = []
    events = []          # ('box', [...]) / ('opt', text)
    skip = False

    def flush_seg():
        nonlocal cur
        t = ''.join(cur)
        cur = []
        t = t.strip()
        # 源内 `[ＢＧＭ停止]\]\` 的零宽残留（仅反斜杠/方括号，不上屏）
        if t and re.fullmatch(r'[\\\[\]]+', t):
            return
        if t:
            segs.append(t)

    def flush_box():
        nonlocal segs
        flush_seg()
        if segs:
            events.append(('box', list(segs)))
        segs = []

    for ln in lines:
        s = ln.strip()
        if skip:
            if s.startswith('*'):
                skip = False
            else:
                continue
        if not s:
            continue
        if s.startswith(';'):
            continue
        if s.startswith('@'):
            continue
        if s.startswith('*'):
            # 标签行：*name|title
            lab = s[1:].split('|')[0].strip()
            if SKIP_FROM_LABEL.get(name) and lab.startswith(SKIP_FROM_LABEL[name]):
                skip = True
            continue
        # 去掉行尾续行符
        s = s.rstrip()
        if s.endswith('\\'):
            s = s[:-1]
        for kind, val in scan_tags(s):
            if kind == 't':
                if in_option:
                    opt.append(val)
                else:
                    cur.append(val)
                continue
            tn = tag_name(val)
            if tn == 'plc' or tn == 'p':
                if in_option:
                    continue
                flush_box()
            elif tn == 'l':
                if in_option:
                    continue
                flush_seg()
            elif tn in ('ct', 'er', 'cm'):
                if in_option:
                    continue
                if ''.join(cur).strip() or segs:
                    flush_box()
            elif tn == 'emb':
                m = re.search(r'exp\s*=\s*"([^"]*)"', val)
                if m and m.group(1) == 'sf.名前':
                    (opt if in_option else cur).append(DEFAULT_NAME)
            elif tn == '選択肢':
                flush_box()
                in_option = True
                opt = []
            elif tn == '選択済み':
                t = ''.join(opt).strip()
                if t:
                    events.append(('opt', t))
                opt = []
                in_option = False
    if segs or ''.join(cur).strip():
        flush_box()
    return events


def main():
    X = XP3(XP3PATH)
    events = []
    for f in FILES:
        n = 'scenario/' + f
        ev = extract(f, X.read(n).decode('cp932'))
        nb = sum(1 for k, _v in ev if k == 'box')
        no = sum(1 for k, _v in ev if k == 'opt')
        nm = sum(1 for k, v in ev if k == 'box' and len(v) >= 2)
        print('%-22s boxes=%-5d multi=%-3d opts=%d' % (f, nb, nm, no))
        events.extend(ev)

    # 跨框断引号/括号：单行「无」/（无）成组 → 段行＋合并行
    out = []    # (lines)
    i = 0
    n_ev = len(events)

    def unbalanced(t, o, c):
        return t.count(o) > t.count(c)

    while i < n_ev:
        kind, val = events[i]
        if kind == 'opt':
            out.append(('opt', val)); i += 1; continue
        segs = val
        # 跨框组：仅当本框最后一个段「全角开括号未闭」且下一框是纯续行（不以「/（开头）
        merged = list(segs)
        j = i + 1
        while j < n_ev and j <= i + 3:
            k2, v2 = events[j]
            if k2 != 'box':
                break
            first = v2[0]
            need_q = any(unbalanced(x, '「', '」') for x in merged)
            need_p = any(unbalanced(x, '（', '）') for x in merged)
            if not need_q and not need_p:
                break
            if first.startswith('「') or first.startswith('（'):
                break
            merged.extend(v2)
            j += 1
        if j > i + 1:
            out.extend(('seg', x) for x in merged)
            out.append(('merged', ''.join(merged)))
            i = j
        else:
            if len(segs) >= 2:
                out.extend(('seg', x) for x in segs)
                out.append(('merged', ''.join(segs)))
            else:
                out.append(('line', segs[0]))
            i += 1

    lines = [v for _k, v in out]
    body = ''.join(x + '\n' for x in lines)
    stats = {
        'lines': len(lines),
        'segs': sum(1 for k, _v in out if k == 'seg'),
        'merged': sum(1 for k, _v in out if k == 'merged'),
        'opts': sum(1 for k, _v in out if k == 'opt'),
    }
    print('成品 %d 行（段行 %d / 合并行 %d / 选项 %d）' % (
        stats['lines'], stats['segs'], stats['merged'], stats['opts']))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'wb') as f:
        f.write(b'\xef\xbb\xbf' + body.encode('utf-8'))
        f.write(b'')
    print('写出 %s（%d B, %d 字）' % (OUT, os.path.getsize(OUT), sum(len(x) for x in lines)))
    # 自检
    bad1 = [(i + 1, x) for i, x in enumerate(lines) if '「' in x and '」' not in x]
    bad2 = [(i + 1, x) for i, x in enumerate(lines) if '（' in x and '）' not in x]
    print('含「无」 %d 行；含（无） %d 行' % (len(bad1), len(bad2)))
    for a in bad1[:10]:
        print('  Q', a[0], a[1][:60])
    for a in bad2[:10]:
        print('  P', a[0], a[1][:60])


if __name__ == '__main__':
    main()
