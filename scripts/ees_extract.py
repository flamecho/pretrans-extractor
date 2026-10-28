#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""END END SUMMER (KiriKiri / KAG3 派生) 文本提取 —— 双版对照

L0 断框判据（引擎源码 system/MainWindow.tjs 标签分派表）：
  l : function(elm)  // 行クリック待ち → showLineBreak() → conductor.wait(%[click…])
  p : function(elm)  // ページクリック待ち → showPageBreak() → conductor.wait(%[click…])
  r : function(elm)  // 改行（无等待）—— 本作脚本 0 次
  ct/cm/c : 清窗（clearMessageLayers…，无等待）
⇒ 「框内等待（不清框）」与「换页等待」是两条独立指令 ⇒ 双指令 ⇒ 只交双版对照：
   屏 = 两次清窗之间；屏内每段（l/p 分隔）先逐段列出，再列合并行；单段屏不重复。
  [link]…[endlink] = 画面内可点文本 = 选项（一行一条，不参与合并）
  [emb exp=f.name]→沙耶 / [emb exp=f.name2]→宮野（first.ks 默认值）
"""
import re, sys, os

NAME = '沙耶'      # f.name   （first.ks: f.name='沙耶'）
FAMILY = '宮野'    # f.name2  （first.ks: f.name2='宮野'）

SRC = ['ees1', 'ees2', 'ees3', 'ees4']
TAG = re.compile(r'\[([^\]]*)\]')
CLEAR_TAGS = {'c', 'cm', 'ct', 'rec'}


def tokenize(text):
    pos = 0
    for m in TAG.finditer(text):
        if m.start() > pos:
            yield ('text', text[pos:m.start()])
        body = m.group(1)
        parts = body.split(None, 1)
        name = parts[0].strip() if parts else ''
        args = parts[1].strip() if len(parts) > 1 else ''
        yield ('tag', name, args, body)
        pos = m.end()
    if pos < len(text):
        yield ('text', text[pos:])


def clean(s):
    return s.strip(' \u3000\t\r\n')


def emit_frame(segs, out, stats):
    """segs: 屏内各段（已 clean，可能含空段）"""
    segs = [s for s in segs if s]
    if not segs:
        return
    if len(segs) == 1:
        out.append(segs[0])
        stats['single'] = stats.get('single', 0) + 1
        return
    out.extend(segs)
    out.append(''.join(segs))
    stats['dual'] = stats.get('dual', 0) + 1
    stats['maxseg'] = max(stats.get('maxseg', 0), len(segs))


def extract(path, out, stats):
    raw = open(path, 'rb').read().decode('cp932')
    keep = []
    for ln in raw.split('\n'):
        ln = ln.rstrip('\r')
        s = ln.strip()
        if s.startswith('\\'):
            s = s[1:]
        if s.endswith('\\'):          # KAG 行末 \ = 行連結
            s = s[:-1]
        st = s.strip()
        if not st:
            keep.append('')
            continue
        if st[0] in '*;@':
            continue
        keep.append(s)
    raw = '\n'.join(keep)

    segs, cur = [], []
    in_link, link_buf = False, []

    def cut_seg():
        segs.append(clean(''.join(cur)))
        cur.clear()

    for tok in tokenize(raw):
        if tok[0] == 'text':
            t = tok[1].replace('\r', '').replace('\n', '')
            if in_link:
                link_buf.append(t)
            else:
                cur.append(t)
            continue
        _, name, args, body = tok
        if name == 'emb':
            m = re.search(r'exp=(f\.name2?)\b', args)
            if m:
                cur.append(FAMILY if m.group(1) == 'f.name2' else NAME)
            else:
                stats.setdefault('emb_other', []).append(body)
            continue
        if name == 'link':
            cut_seg()
            emit_frame(segs, out, stats)      # 选项前先把同框正文收口
            segs.clear()
            in_link, link_buf = True, []
            stats['choices'] = stats.get('choices', 0) + 1
            continue
        if name in ('endlink', '/endlink'):
            in_link = False
            opt = clean(''.join(link_buf))
            if opt:
                out.append(opt)
            link_buf = []
            continue
        if in_link:
            continue
        if name in ('l', 'p', 's'):     # 均为クリック待ち → 一次点击 = 一段
            cut_seg()
            stats['clicks'] = stats.get('clicks', 0) + 1
            continue
        if name in CLEAR_TAGS:          # 清窗 → 一屏结束
            cut_seg()
            emit_frame(segs, out, stats)
            segs.clear()
            continue
    cut_seg()
    emit_frame(segs, out, stats)


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else '提取结果'
    allout, stats = [], {}
    for f in SRC:
        p = os.path.join('_work_ees/x', 'scenario__%s.ks' % f)
        before = len(allout)
        extract(p, allout, stats)
        print(f, '+%d lines' % (len(allout) - before))
    print('stats', stats)
    os.makedirs(outdir, exist_ok=True)
    dst = os.path.join(outdir, '[PC-JP]END END SUMMER.txt')
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(allout) + '\n')
    print('wrote', dst, len(allout), 'lines')


if __name__ == '__main__':
    main()
