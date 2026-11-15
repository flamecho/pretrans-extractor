# -*- coding: utf-8 -*-
"""七人の性奴隷 / Seven Sex Slaves（KiriKiri2 + KAG3）剧本 -> 全文本（双版）

用法: python scripts/sss_extract.py --dir _work_sss/x/scenario --out "提取结果/[JP]Seven Sex Slaves.txt"

断框判据（L0，全部取自 system/MainWindow.tjs / system/Config.tjs / scenario/macro.ks）：
  [l]  MainWindow.tjs:4822 -> showLineBreak(elm)   等点击、不清屏  => 段界
  [p]  MainWindow.tjs:4828 -> showPageBreak(elm)   等点击、不清屏  => 段界（不是框界！）
  [waitclick] 等点击、不清屏                        => 段界
  [r]  MainWindow.tjs:4701 -> processReturn()      框内改行       => 合并
  [er] MainWindow.tjs:4867 -> current.clear()                      => 页界
  [cm] MainWindow.tjs:4858 -> clearMessageLayers(false)            => 页界
  [ct] MainWindow.tjs:4849 -> clearMessageLayers(true)             => 页界
  [>]  macro.ks = [p][hr][cm][cf]  => 点一次 + 清一框（作者每句末尾的定式）
  [黒帯下]/[黒帯中央] macro.ks 内含 [cm]                           => 页界
  Config.tjs:26 `;global.ignoreCR = true;` 注释掉 => false：脚本物理换行＝框内换行 => 合并
  macro.ks 的 [「] [」] [（] [）] [『] [』] 是**输出引号字符**的文本宏 => 按字符保留
  [ch text="…"] = 直接上屏字符；[ruby text="…"] 只注音 => 丢注留基底

一行 = 一次点击。同一页（无 cm/er/ct 间隔）内多次点击 => 段行 + 合并行（双版）。
"""
import argparse
import io
import os
import re
import sys

# 主图表 main.ks 的 [call storage=…] 顺序；10ha/10hb + end1 为结局，其后为 b_lose.ks 的 BAD 分支
FILES = [
    '1A', '2A', '2B', '2h', '2_1',
    '3', '3h', '3_1', '4', '4h', '4_1',
    '5', '5h', '5_1', '6', '7', '7h', '7_1',
    '8', '8h', '8h_1', '8_1', '9', '9h', '9_1',
    '10', '10_1', '10ha', '10hb', 'end1',
    'abad', 'abad_1', 'bad', 'badh',
]

CHARMACRO = {'「': '「', '」': '」', '（': '（', '）': '）', '『': '『', '』': '』'}
PAGEMACRO = {'黒帯下', '黒帯中央', 'エンドロール'}
SEG_TAGS = {'l', 'p', 'waitclick'}
PAGE_TAGS = {'cm', 'er', 'ct'}


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
    """('text', str) / ('tag', name, attrs)；`[`…`]` 按深度配平，引号内的 `]` 不截断。"""
    out, i, n, buf = [], 0, len(s), ''
    while i < n:
        c = s[i]
        if c != '[':
            buf += c
            i += 1
            continue
        j, depth, q = i, 0, ''
        while j < n:
            ch = s[j]
            if q:
                if ch == q:
                    q = ''
            elif ch in '"\'':
                q = ch
            elif ch == '[':
                depth += 1
            elif ch == ']':
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
            out.append(('text', buf))
            buf = ''
        inner = s[i + 1:j]
        m = re.match(r'([^\[\]\s=]+)', inner)
        out.append(('tag', m.group(1) if m else '', inner))
        i = j + 1
    if buf:
        out.append(('text', buf))
    return out


def attr(attrs, key):
    m = re.search(r'\b' + key + r'="([^"]*)"', attrs)
    return m.group(1) if m else None


def parse(path):
    text = read_ks(path)
    pages, choices = [], []
    segs, cur = [], ''
    st = dict(clicks=0, clears=0, pages=0, segments=0, multi=0, choices=0, chars=0,
              ch=0, ruby=0, macro_q=0, macro_page=0, stray=0)
    in_script = False

    def close_seg():
        nonlocal cur
        s = cur
        cur = ''
        if s.strip():
            segs.append(s)

    def close_page():
        nonlocal segs
        close_seg()
        if segs:
            pages.append(list(segs))
        segs.clear()

    for raw in text.split('\n'):
        line = raw.strip(' \t\r')
        s = line
        if in_script:
            if 'endscript' in s.lower():
                in_script = False
            continue
        if s.lower().startswith(('[iscript', '@iscript')):
            in_script = True
            continue
        if not s or s.startswith((';', '*')):
            continue
        if s.startswith('@'):
            line = '[' + s[1:].strip() + ']'
        for tok in split_tags(line):
            if tok[0] == 'text':
                t = tok[1].replace('\r', '')
                if t.strip(' \t'):
                    if not t.strip(' \t').strip(']'):
                        st['stray'] += 1   # 9_1.ks:484 `[return]]` 的尾随 `]`，return 先跳走 => 不上屏
                        continue
                    cur += t
                    st['chars'] += len(t)
                continue
            name, attrs = tok[1], tok[2]
            if name == 'r':
                continue
            if name in SEG_TAGS:
                st['clicks'] += 1
                close_seg()
            elif name in PAGE_TAGS:
                st['clears'] += 1
                close_page()
            elif name == '>':
                st['clicks'] += 1
                st['clears'] += 1
                close_page()
            elif name in PAGEMACRO:
                st['clears'] += 1
                st['macro_page'] += 1
                close_page()
            elif name in CHARMACRO:
                cur += CHARMACRO[name]
                st['chars'] += 1
                st['macro_q'] += 1
            elif name == 'ch':
                t = attr(attrs, 'text')
                if t:
                    cur += t
                    st['chars'] += len(t)
                st['ch'] += 1
            elif name == 'ruby':
                st['ruby'] += 1
            elif name == 'slctbtn':
                t = attr(attrs, 'str')
                if t:
                    choices.append(t)
                    st['choices'] += 1
            # 其余标签（eval/if/endif/image/BGM/…）不影响正文
    close_page()

    rows = []
    st['pages'] = len(pages)
    for v in pages:
        rows.extend(v)
        st['segments'] += len(v)
        if len(v) >= 2:
            rows.append(''.join(v))
            st['multi'] += 1
    rows.extend(choices)
    return rows, st, pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    d = a.dir
    rows = []
    total = dict(clicks=0, clears=0, pages=0, segments=0, multi=0, choices=0, chars=0,
                 ch=0, ruby=0, macro_q=0, macro_page=0, stray=0)
    for fn in FILES:
        r, st, _ = parse(os.path.join(d, fn + '.ks'))
        rows.extend(r)
        for k in total:
            total[k] += st[k]
        print('%-10s %s' % (fn, st), file=sys.stderr)
    with io.open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        for s in rows:
            f.write(s + '\n')
    print('TOTAL %s' % total, file=sys.stderr)
    print('lines %d = segments %d + merged %d + choices %d'
          % (len(rows), total['segments'], total['multi'], total['choices']), file=sys.stderr)


if __name__ == '__main__':
    main()
