# -*- coding: utf-8 -*-
"""[JP]アカシア通り一番地 — KiriKiri XP3 ＋ KAG3 全文本提取（双版对照）

来源: `[JP]アカシア通り一番地.exe`（RAR5 SFX，密码 otoame）→ `data.xp3`（279 成员）
正文: `scenario/main.ks`（175,980 B / 5,184 行）。其余 .ks 为系统/菜单/STAFF 插件，无剧情。

断框判据（引擎级，`system/MainWindow.tjs`）:
- 页界（清屏＋点击）= `[p]`(4407 showPageBreak) / `[P]`(大写，逐处均位于页尾，
  其后至下一次清屏之间无正文，断框位置与 `[p]` 一致) / `[cm]`(4437 clearMessageLayers)
  / `[ct]` / `[er]`；源码 `@cm` 同义。
- 段界（框内点击，不清屏）= `[l]`(4401 showLineBreak) / `[s]`(4540 実行停止, inSleep)。
  `chNonStopToPageBreak = false`（MainWindow.tjs:124）⇒ `[l]` 真会停，非自动读到底。
- `[r]`(4280 改行) = 软换行；物理换行 = 续行 ⇒ 一律 `''` 拼接。
- 选项 = `[link target=*label]TEXT[endlink]`，`Ａ：`/`Ｂ：` 前缀用 PREFIX_RE 拼回。
- 名窗: 本作无独立名字窗，正文内无名札（`[message0]`/`【` 均 0 命中）。

双版: 一页 ≥2 段（≥2 次点击）⇒ 段行 + 同页合并行；选项各占一行，置于合并行之后。
输出: UTF-8 BOM / 纯 LF / 一行 = 一次点击。
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xp3 import XP3

KS = 'scenario/main.ks'
TAG_RE = re.compile(r'\[[^\]]*\]')
LINK_RE = re.compile(r'\[link[^]]*?\](.*?)\[endlink\]', re.S)
PREFIX_RE = re.compile(r'^[　 \t]*[Ａ-Ｚ０-９甲乙丙丁一二三四五六七八九十][　 \t]*[：:]?[　 \t]*$')
JP = re.compile(r'[぀-ヿ㐀-鿿　-〿＀-￯]')

PAGE_RE = re.compile(r'\[(p|P|cm|ct|er)\]')
SEG_RE = re.compile(r'\[(l|s)\]')
CMT_RE = re.compile(r'^\s*;')
LAB_RE = re.compile(r'^\s*\*')
AT_RE = re.compile(r'^\s*@')


def load_lines(path):
    b = open(path, 'rb').read()
    if b[:3] == b'\xef\xbb\xbf':
        t = b.decode('utf-8-sig')
    else:
        t = b.decode('cp932', 'replace')
    return t.replace('\r\n', '\n').replace('\r', '\n').split('\n')


def join_script(lines):
    kept = []
    for ln in lines:
        st = ln.strip()
        if not st:
            continue
        if CMT_RE.match(ln) or LAB_RE.match(ln):
            continue
        if AT_RE.match(ln):
            m = re.match(r'@(cm|ct|er)\s*$', st)
            if m:
                kept.append('[%s]' % m.group(1))
            continue
        kept.append(ln)
    return ''.join(kept)


def strip_tags(s):
    return TAG_RE.sub('', s)


def process_segment(raw):
    """段内：拆选项（link 内文本）＋ 其余文本。返回 (seg_texts, opt_texts)。"""
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


def extract(text, stats):
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    pages = []
    for rp in PAGE_RE.split(join_script(text.split('\n'))):
        segs, opts = [], []
        for rs in SEG_RE.split(rp):
            st, ot = process_segment(rs)
            segs.extend(x.strip() for x in st if x.strip())
            opts.extend(x.strip() for x in ot if x.strip())
        pages.append((segs, opts))
    return pages


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--xp3', required=True)
    ap.add_argument('--out')
    ap.add_argument('--verify', action='store_true')
    a = ap.parse_args()

    x = XP3(a.xp3)
    if KS not in x.files:
        raise SystemExit('缺脚本 ' + KS)
    pages = extract(x.read(KS).decode('cp932', 'replace'), {})

    lines = []
    n_pages = n_multi = n_seg = n_opt = 0
    page_net = []           # 每页（段+选项，不含合并行）引号净差
    single_unbal = 0        # 单段页（无合并行）里的不平衡行
    for segs, opts in pages:
        if not segs and not opts:
            continue
        n_pages += 1
        txt = ''.join(segs) + ''.join(opts)
        page_net.append(txt.count('「') - txt.count('」'))
        for s in segs:
            lines.append(s)
            n_seg += 1
        if len(segs) >= 2:
            lines.append(''.join(segs))
            n_multi += 1
        else:
            single_unbal += sum(1 for s in segs
                                if s.count('「') != s.count('」')
                                or s.count('（') != s.count('）'))
        for o in opts:
            lines.append(o)
            n_opt += 1

    print('页(非空) %d / 段行 %d / 多段页 %d / 选项行 %d / 总行 %d'
          % (n_pages, n_seg, n_multi, n_opt, len(lines)))
    print('字数 %d' % sum(len(s) for s in lines))
    unbal_q = sum(1 for s in lines if s.count('「') != s.count('」'))
    unbal_p = sum(1 for s in lines if s.count('（') != s.count('）'))
    print('引号不平衡行 %d / 括号不平衡行 %d（段行半闭属双版预期）' % (unbal_q, unbal_p))
    print('单段页内不平衡行 %d（=0 则所有半闭行都在多段页，合并行闭合）' % single_unbal)
    # 页级：某页净「>0 ⇒ 该页结束时引号仍未闭合 ⇒ 跨框断引号
    cross = sum(1 for n in page_net if n > 0)
    print('页级未闭合引号 %d 页 ⇒ 跨框断引号 %d 组（不合并）' % (cross, cross))
    neg = [(i + 1, n) for i, n in enumerate(page_net) if n < 0]
    for i, n in neg:
        print('  页#%d 净差 %d（选项分支共用同一开引号，属原文）' % (i, n))

    if a.out and not a.verify:
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        with open(a.out, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\ufeff')
            f.write('\n'.join(lines))
            f.write('\n')
        print('写出 %s（%d B）' % (a.out, os.path.getsize(a.out)))


if __name__ == '__main__':
    main()
