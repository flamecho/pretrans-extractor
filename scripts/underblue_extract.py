# -*- coding: utf-8 -*-
"""[JP]アンダーブルー2012 — KiriKiri XP3 ＋ KAG3 全文本提取（双版对照）

源: `[JP]アンダーブルー2012.exe`（RAR5 SFX，密码 otoame）→ `data.xp3`（167 成员）
正文: `scenario/first.ks`（本篇：opening〜ed1/ed2）＋ `scenario/omake.ks`（おまけ／エクストラ）。
其余 .ks 为系统/菜单/存档/CG/STAFF 字幕/插件。

断页判据（L0，引擎处理器 + 宏）:
- `[plc]`（`macsab.ks:4` 宏）= `@p @cm @label @cm` ⇒ 清屏＋点击 ⇒ **页结束**（first 267 / omake 167）
- `[p]`(MainWindow.tjs:4797 showPageBreak) / `[cm]`(4827 clearMessageLayers) /
  `[ct]`(4818) / `[er]`(4836) ⇒ 清屏 ⇒ **页结束**
- `[l]`(4791 showLineBreak) / `[s]`(4930 inSleep) ⇒ 点击不清屏 ⇒ **页内一次点击（段界）**
- `[r]`(4670 processReturn) ⇒ 软换行、无点击 ⇒ 合并；物理换行＝续行 ⇒ `''` 拼接
- `[delay speed=nowait]` ⇒ chSpeed=0（3416-3420）；若无点击即 `[ct]/[er]` 清屏 ⇒ 该文本未被呈现
  （`＊　＊　＊` 场景分隔 与 选择后的 `Ａ．/Ｂ．` 回声），不作为正文
- 名札 `@平泉/@凛太/@良川/@草間` = `macsab.ks` 宏体 `[nowait]【名】[r][endnowait]`
  ⇒ 名字内联在正文框，**与同一击的台词同行保留**（`--inline-name`）
- `[title name=…]`（MainWindow.tjs:4923 setTitle）＝**窗口标题**，非上屏正文 ⇒ 不收
- 选项 `[link target=*x]…[endlink]`（first.ks 2 个＝1 选择点×2）；`[s]`＝选择点击

双版: 页内 ≥2 次点击 ⇒ 段行＋整页行；单次点击页只出一行。
输出: UTF-8 BOM / 纯 LF / 一行＝一次点击。
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xp3 import XP3

STORIES = ['scenario/first.ks', 'scenario/omake.ks']
MACRO_FILE = 'scenario/macsab.ks'
TAG_RE = re.compile(r'\[[^\]]*\]')
LINK_RE = re.compile(r'\[link[^]]*?\](.*?)\[endlink\]', re.S)
PREFIX_RE = re.compile(r'^[　 \t]*[Ａ-Ｚ０-９甲乙丙丁一二三四五六七八九十][　 \t]*[．：:\.]?[　 \t]*$')
JP = re.compile(r'[぀-ヿ㐀-鿿　-〿＀-￯]')

BOUND_RE = re.compile(r'\[(plc|p|cm|ct|er)\]')
CLICK_BOUND = {'plc', 'p'}
SEG_RE = re.compile(r'\[(l|s)\]')
CMT_RE = re.compile(r'^\s*;')
LAB_RE = re.compile(r'^\s*\*')
AT_RE = re.compile(r'^\s*@')


def read_ks(x, name):
    return x.read(name).decode('cp932', 'replace').replace('\r\n', '\n').replace('\r', '\n')


def parse_macros(text):
    """返回 name -> 宏体文本（仅名字宏：宏体含【】）。支持 [macro ...] 与 @macro ... 声明。"""
    m = {}
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        mm = re.match(r'[@\[]?macro\s+name=["\']?(.+?)["\']?\]?\s*$', s, re.I)
        if not mm:
            i += 1
            continue
        name = mm.group(1).strip()
        body, i = [], i + 1
        while i < len(lines) and not re.match(r'[@\[]?endmacro', lines[i].strip(), re.I):
            body.append(lines[i])
            i += 1
        i += 1
        body_lines = [ln for ln in body if not ln.strip().startswith(';')]
        b = ''.join(x.strip() for x in body_lines)
        if '【' in b and '】' in b:
            m[name] = b
    return m


def join_script(text, names):
    kept = []
    in_script = False
    for ln in text.split('\n'):
        st = ln.strip()
        if in_script:
            if st.startswith('@endscript') or st == '[endscript]':
                in_script = False
            continue
        if st.startswith('@iscript') or st == '[iscript]':
            in_script = True
            continue
        if not st:
            continue
        if CMT_RE.match(ln) or LAB_RE.match(ln):
            continue
        if AT_RE.match(ln):
            cmd = st[1:].strip()
            m = re.match(r'(plc|cm|ct|er)\s*$', cmd)
            if m:
                kept.append('[%s]' % m.group(1))
                continue
            nm = cmd.split()[0] if cmd else ''
            if nm in names:
                kept.append(names[nm])
            continue
        kept.append(ln)
    return ''.join(kept)


def strip_tags(s):
    return TAG_RE.sub('', s)


def process_segment(raw):
    segs, opts = [], []
    pos = 0
    for m in LINK_RE.finditer(raw):
        before = strip_tags(raw[pos:m.start()]).strip()
        inner = strip_tags(m.group(1)).strip()
        pos = m.end()
        if inner:
            if before and PREFIX_RE.match(before):
                opt = before + inner
            elif before:
                if JP.search(before):
                    segs.append(before)
                opt = inner
            else:
                opt = inner
            if opt and JP.search(opt):
                opts.append(opt)
        elif before and JP.search(before):
            segs.append(before)
    after = strip_tags(raw[pos:]).strip()
    if after and JP.search(after):
        segs.append(after)
    return segs, opts


def is_presented(chunk, boundary):
    """该页文本是否真的上屏：页末点击(plc/p)，或文本后有 l/s/选项 点击。"""
    last_text = -1
    for m in re.finditer(r'(?s)(?:(?<=^)|(?<=\]))([^\[]*)', chunk):
        s = m.group(1)
        if s.strip():
            last_text = m.end()
    if last_text < 0:
        return True
    if boundary in CLICK_BOUND:
        return True
    last_click = -1
    for m in TAG_RE.finditer(chunk):
        t = m.group(0)
        if t in ('[l]', '[s]') or t.startswith('[link') or t == '[endlink]':
            last_click = m.end()
    return last_click > last_text


def extract_page(chunk):
    segs, opts = [], []
    for rs in SEG_RE.split(chunk):
        st, ot = process_segment(rs)
        segs.extend(x.strip() for x in st if x.strip())
        opts.extend(x.strip() for x in ot if x.strip())
    return segs, opts


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--xp3', required=True)
    ap.add_argument('--out')
    ap.add_argument('--verify', action='store_true')
    a = ap.parse_args()

    x = XP3(a.xp3)
    names = parse_macros(read_ks(x, MACRO_FILE)) if MACRO_FILE in x.files else {}

    present_pages = []
    dropped = []
    for fn in STORIES:
        J = join_script(read_ks(x, fn), names)
        parts = BOUND_RE.split(J)
        # parts = [text, bound, text, bound, text...]
        for i in range(0, len(parts) - 1, 2):
            chunk, boundary = parts[i], parts[i + 1]
            if not is_presented(chunk, boundary):
                t = strip_tags(chunk).strip()
                if JP.search(t) or '＊' in t:
                    dropped.append(t)
                continue
            segs, opts = extract_page(chunk)
            if segs or opts:
                present_pages.append((segs, opts))
        # 末尾残余（无页末标签）
        tail = parts[-1]
        if tail.strip():
            t = strip_tags(tail).strip()
            if JP.search(t) and is_presented(tail, ''):
                present_pages.append(extract_page(tail))

    lines = []
    n_pages = n_seg = n_multi = n_opt = 0
    page_net = []
    single_unbal = 0
    for segs, opts in present_pages:
        n_pages += 1
        txt = ''.join(segs) + ''.join(opts)
        page_net.append(txt.count('「') - txt.count('」'))
        for s in segs:
            lines.append(s); n_seg += 1
        if len(segs) >= 2:
            lines.append(''.join(segs)); n_multi += 1
        else:
            single_unbal += sum(1 for s in segs
                                if s.count('「') != s.count('」') or s.count('（') != s.count('）'))
        for o in opts:
            lines.append(o); n_opt += 1

    print('页(上屏) %d / 段行 %d / 多点击页(整页行) %d / 选项行 %d / 总行 %d'
          % (n_pages, n_seg, n_multi, n_opt, len(lines)))
    print('字数 %d' % sum(len(s) for s in lines))
    print('引号不平衡行 %d / 括号不平衡行 %d'
          % (sum(1 for s in lines if s.count('「') != s.count('」')),
             sum(1 for s in lines if s.count('（') != s.count('）'))))
    print('单点击页内不平衡行 %d' % single_unbal)
    cross = sum(1 for n in page_net if n > 0)
    print('页级未闭合引号 %d 页 ⇒ 跨页断引号 %d 组' % (cross, cross))
    neg = [(i + 1, n) for i, n in enumerate(page_net) if n < 0]
    for i, n in neg:
        print('  页#%d 净差 %d' % (i, n))
    print('--- 未上屏丢弃文本 %d 条:' % len(dropped))
    for d in dropped:
        print('   %r' % d[:80])

    if a.out and not a.verify:
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        with open(a.out, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\ufeff')
            f.write('\n'.join(lines))
            f.write('\n')
        print('写出 %s（%d B）' % (a.out, os.path.getsize(a.out)))


if __name__ == '__main__':
    main()
