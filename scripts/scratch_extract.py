"""SCRATCH (undo/大樹愁 2006, KiriKiri2 KAG3) 剧本文本提取 —— 双版对照（段行＋合并行）。

L0 判据（system/Config.tjs ＋ system/MainWindow.tjs ＋ script/macro.ks）：
  [l]  = tagHandlers.l → showLineBreak：行クリック待ち（只等待，不清屏）⇒ 段边界
  [p]  = tagHandlers.p → showPageBreak：页面クリック待ち（本 build 的 handler 只
         `historyLayer.reline()` ＋ wait，不清屏；clear2 只用于自动溢出）
         ⇒ 段边界，但**不是**框边界（与 REstart 那版不同，勿套用）
  [pc] = macro.ks 自定义宏 = [label][cm]；[label] 无 handler（KAG 忽略）⇒ [cm] 清框
  [er]/[cm]/[ct] = current.clear() / clearMessageLayers ⇒ 框（页）边界（L0）
  [s]  = 停止（选项/跳转等待），不清屏 ⇒ 不作框边界
  Config.tjs `;global.ignoreCR = false;`（注释=默认 false，KAG3 默认）
         ⇒ 脚本物理换行＝框内换行 ⇒ 一律并入同行（不拆）
  mes_* 宏 = [font …][nowait]【名】[endnowait] 画进 message0 正文框（无独立名字窗）
         ⇒ 名札保留接在同行台词前（品检 --inline-name）
  [link2 …]text[endlink2] / [link target=*…]text[endlink] = 叙事选项 ⇒ 一行一条
  *label|表示名 的 |表示名 不上屏 ⇒ 剥离
  card_mako_normal.ks 被 card_hit_mako.ks 引用但包内不存在（337 成员全清单核实）⇒ 死链

用法：python scripts/scratch_extract.py --dir _work_scratch/x/scenario --out "提取结果/[JP]Scratch.txt"
"""
import argparse
import io
import pathlib
import re
import sys

BS = chr(92)
Q = chr(39)
TAG = re.compile(r'\[(?:[^\[\]"' + Q + r']|"[^"]*"|' + Q + r'[^' + Q + r']*' + Q + r')*\]|^@(\w+)([^\n]*)', re.M)
ATTR = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*("([^"]*)"|\'([^\']*)\'|([^\s\]]+))')

NAMES = {'mes_ore': '【広崎 倭人】', 'mes_yosi': '【比嘉 由実】',
         'mes_mako': '【高梨 真琴】', 'mes_shin': '【我妻 　深】',
         'mes_shuri': '【藤堂 朱莉】'}
KEEP = set(NAMES) | {'l', 'p', 'er', 'cm', 'ct', 'pc', 's', 'waitclick',
                     'link', 'link2', 'endlink', 'endlink2'}

# 显示顺序：本篇路线 → 卡片对战（入口＋各角 gameplay）→ 后记 → 未引用旧稿
FILES = [
    'main.ks', 'main2.ks', 'yosi.ks', 'shin.ks', 'shuri.ks', 'mako.ks', 'ending.ks',
    'card.ks', 'card_hit_yosi.ks', 'card_hit_shin.ks', 'card_hit_shuri.ks', 'card_hit_mako.ks',
    'card_yosi01.ks', 'card_yosi02.ks', 'card_yosi03.ks',
    'card_yosi_easy.ks', 'card_yosi_normal.ks', 'card_yosi_muzu.ks',
    'card_shin01.ks', 'card_shin02.ks', 'card_shin03.ks',
    'card_shin_easy.ks', 'card_shin_normal.ks', 'card_shin_muzu.ks',
    'card_shuri01.ks', 'card_shuri02.ks', 'card_shuri03.ks',
    'card_shuri_easy.ks', 'card_shuri_normal.ks', 'card_shuri_muzu.ks',
    'card_mako01.ks', 'card_mako02.ks', 'card_mako03.ks',
    'card_mako_easy.ks', 'card_mako_muzu.ks',
    'undo.ks',
    # 未引用旧稿（包内存在、无入口引用；含独有台词，附末尾防漏）
    'main0.ks', 'card_yosi.ks', 'card_yosi2.ks', 'card_yosi0.ks', 'card_yosi_old.ks',
]


def attrs(s):
    d = {}
    for m in ATTR.finditer(s):
        d[m.group(1)] = m.group(3) if m.group(3) is not None else (
            m.group(4) if m.group(4) is not None else m.group(5))
    return d


def parse(path):
    raw = path.read_bytes().decode('cp932')
    raw = raw.replace('\r\n', '\n').replace('\r', '\n')
    raw = re.sub(r'\[iscript\].*?\[endscript\]', '', raw, flags=re.S)
    lines = [ln for ln in raw.split('\n') if not ln.strip().startswith(';')]
    text = '\n'.join(lines)
    # 先剥「非结构标签」（引号感知；@行式整行剥），再剥 *label —— 顺序不可反：
    # 标签属性里有 target=*xxx，先剥 label 会把属性打碎导致标签失配残留。
    # 结构标签（断框/选项/名札）保留给下方事件循环。
    def keep(m):
        body = m.group(0)
        if body.startswith('@'):
            nm = m.group(1)
        else:
            nm = re.match(r'\[([a-zA-Z_][a-zA-Z0-9_]*)', body)
            nm = nm.group(1) if nm else ''
        return body if nm in KEEP else ''
    text = TAG.sub(keep, text)
    text = re.sub(r'\*[A-Za-z0-9_]+\|[^\n]*', '', text)
    text = re.sub(r'\*[A-Za-z0-9_]+', '', text)
    text = text.replace(BS + '\n', '')          # 显式续行
    text = re.sub(re.escape(BS) + r'(?=[@[])', '', text)  # 行中续行符残留
    text = text.rstrip(BS + ' \n')              # 文件尾无换行的续行符（card_yosi0.ks）

    out = []
    segs, buf = [], []
    in_link = False
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
            tag, rest = m.group(1), m.group(2)
        else:
            body = m.group(0)[1:-1]
            nm = re.match(r'([a-zA-Z_][a-zA-Z0-9_]*)', body)
            tag = nm.group(1) if nm else ''
            rest = body[nm.end():] if nm else ''
        a = attrs(rest)
        if tag in ('link', 'link2'):
            flush_seg()
            flush_page()
            in_link = True
            link_buf = []
        elif tag in ('endlink', 'endlink2'):
            t = ''.join(link_buf).replace('\n', '').strip()
            in_link = False
            if t:
                out.append(('choice', t))
        elif tag in ('l', 'p', 'waitclick'):
            n_l += 1
            flush_seg()
        elif tag in ('er', 'cm', 'ct', 'pc'):
            n_clear += 1
            flush_page()
        elif tag in NAMES:
            buf.append(NAMES[tag])
    tail = text[pos:]
    if in_link:
        link_buf.append(tail)
    else:
        buf.append(tail)
    flush_page()
    stats = dict(clicks=n_l, clears=n_clear, pages=sum(1 for k, _ in out if k == 'page'),
                 segments=sum(len(v) for k, v in out if k == 'page'),
                 multi=sum(1 for k, v in out if k == 'page' and len(v) >= 2),
                 choices=sum(1 for k, _ in out if k == 'choice'))
    return out, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    d = pathlib.Path(a.dir)
    rows = []
    total = dict(clicks=0, clears=0, pages=0, segments=0, multi=0, choices=0)
    for fn in FILES:
        out, st = parse(d / fn)
        for kind, v in out:
            if kind == 'page':
                rows.extend(v)
                if len(v) >= 2:
                    rows.append(''.join(v))
            else:
                rows.append(v)
        for k in total:
            total[k] += st[k]
        print('%-22s %s' % (fn, st), file=sys.stderr)
    with io.open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        for s in rows:
            f.write(s + '\n')
    print('TOTAL %s' % total, file=sys.stderr)
    print('lines %d = segments %d + merged %d + choices %d'
          % (len(rows), total['segments'], total['multi'], total['choices']),
          file=sys.stderr)


if __name__ == '__main__':
    main()