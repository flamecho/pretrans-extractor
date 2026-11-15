"""REstart (吉里吉里 KAG3) 剧本文本提取 —— 双版对照（段行＋合并行）。

L0 判据（system/MainWindow.tjs ＋ Config.tjs）：
  [l]  = showLineBreak   行クリック待ち ⇒ 段（一次点击）边界
  [p]  = showPageBreak   ページクリック待ち＋clear（本作 0 处）
  [er]/[cm]/[ct] = current.clear() 无等待 ⇒ 页（框）边界
  [s]  = stop（选项等待）⇒ 收尾当前页
  [r]  = 框内换行（本作 0 处）；Config.tjs `global.ignoreCR=false`
         ⇒ 脚本物理换行也是框内换行 ⇒ 一律并入同行（不拆）
  [hr] = 仅历史层换行，不上屏 ⇒ 忽略
  [nowait]…[endnowait] = 同层内名字，无独立名字窗 ⇒ 名字接在同行台词前
  [link storage=…]text[endlink]（first.ks message3）= 叙事选项 ⇒ 一行一条
  omake.ks 的 [link target=*…] = 菜单导航 ⇒ 排除（*omake〜*oma1 区段整体跳过）
  [type text="…"] = 直接上屏文字 ⇒ 独立一行（前後の待機と別表示イベント）

用法：python scripts/restart_extract.py --dir _work_restart/x/scenario --out 提取结果/[JP]REstart.txt
"""
import argparse
import io
import pathlib
import re
import sys

TAG = re.compile(r'\[([^\[\]]+)\]|@(\w+)([^\n]*)')
ATTR = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*("([^"]*)"|\'([^\']*)\'|([^\s\]]+))')
FILES = ['first.ks', 'k.ks', 't.ks', 'ed.ks', 'omake.ks']


def attrs(s):
    d = {}
    for m in ATTR.finditer(s):
        d[m.group(1)] = m.group(3) if m.group(3) is not None else (
            m.group(4) if m.group(4) is not None else m.group(5))
    return d


def parse(path, skip_until_label=None):
    """返回 (pages, choices, types, stats)。pages = [[segment,...],...]"""
    raw = path.read_bytes().decode('cp932')
    raw = raw.replace('\r\n', '\n').replace('\r', '\n')
    raw = raw.replace('\\\n', '')
    lines = []
    started = skip_until_label is None
    for ln in raw.split('\n'):
        s = ln.strip()
        if not started:
            if s.startswith(skip_until_label):
                started = True
            else:
                continue
        if s.startswith(';'):
            continue
        lines.append(ln)
    text = '\n'.join(lines)
    # 标签行（含 | 后的内部显示名，不上屏）整体剥离；可出现在续行拼接后的行中间
    text = re.sub(r'\*[A-Za-z0-9_]*\|[^\n]*', '', text)
    text = re.sub(r'(?m)^\*[A-Za-z0-9_]+[ \t]*$', '', text)
    # 行中续行符残留：`[jump …]\[s]` 的 `\` 紧贴下一标签 ⇒ 续行语义，非正文
    text = re.sub(r'\\(?=[@[])', '', text)

    pages, segs = [], []
    out = []  # 顺序流：('page', segs) / ('choice', text) / ('type', text)
    buf = []
    in_link = False
    link_is_choice = False
    link_buf = []
    n_l = n_clear = 0

    def flush_seg():
        t = ''.join(buf).replace('\n', '').strip()
        buf.clear()
        if t:
            segs.append(t)

    def flush_page():
        flush_seg()
        if segs:
            out.append(('page', list(segs)))
            segs.clear()

    pos = 0
    for m in TAG.finditer(text):
        chunk = text[pos:m.start()]
        pos = m.end()
        if in_link:
            link_buf.append(chunk)
        else:
            buf.append(chunk)
        if m.group(1) is not None:
            body = m.group(1)
            name = re.match(r'([a-zA-Z_][a-zA-Z0-9_]*)', body)
            tag = name.group(1) if name else ''
            rest = body[name.end():] if name else ''
        else:
            tag = m.group(2)
            rest = m.group(3)
        a = attrs(rest)
        if tag == 'link':
            flush_seg()
            flush_page()
            in_link = True
            link_buf = []
            link_is_choice = 'storage' in a
        elif tag == 'endlink':
            t = ''.join(link_buf).replace('\n', '').strip()
            in_link = False
            if t and link_is_choice:
                out.append(('choice', t))
        elif tag in ('l', 'p'):
            n_l += 1
            flush_seg()
            if tag == 'p':
                flush_page()
        elif tag in ('er', 'cm', 'ct'):
            n_clear += 1
            flush_page()
        elif tag == 's':
            flush_page()
        elif tag == 'type' and 'text' in a:
            flush_seg()
            flush_page()
            out.append(('type', a['text']))
        elif tag == 'ch':
            buf.append(a.get('text', ''))
    tail = text[pos:]
    if in_link:
        link_buf.append(tail)
    else:
        buf.append(tail)
    flush_page()
    pages = [v for k, v in out if k == 'page']
    choices = [v for k, v in out if k == 'choice']
    types = [v for k, v in out if k == 'type']
    stats = dict(clicks=n_l, clears=n_clear, pages=len(pages),
                 segments=sum(len(p) for p in pages),
                 multi=sum(1 for p in pages if len(p) >= 2),
                 choices=len(choices), types=len(types))
    return out, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    d = pathlib.Path(a.dir)
    rows = []
    total = dict(clicks=0, clears=0, pages=0, segments=0, multi=0, choices=0, types=0)
    for fn in FILES:
        skip = '*oma1' if fn == 'omake.ks' else None
        out, st = parse(d / fn, skip)
        for kind, v in out:
            if kind == 'page':
                rows.extend(v)
                if len(v) >= 2:
                    rows.append(''.join(v))
            else:
                rows.append(v)
        for k in total:
            total[k] += st[k]
        print('%-10s %s' % (fn, st), file=sys.stderr)
    with io.open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        for s in rows:
            f.write(s + '\n')
    print('TOTAL %s' % total, file=sys.stderr)
    print('lines %d = segments %d + merged %d + choices %d'
          % (len(rows), total['segments'], total['multi'], total['choices']),
          file=sys.stderr)


if __name__ == '__main__':
    main()