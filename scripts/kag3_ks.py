"""KAG3（KiriKiri 2.x）`.ks` 剧本 → 双版对照文本。

对象：`[JP]Heavenly Blue`（2003, 単一 exe ＝ 207,861,691 B，内嵌 XP3 于 2,478,080；XP3 索引 1,113 项）。

## 断框判据（L0：引擎指令）
- **一次点击**：`[r]`（改行＋クリック待ち）／`[lr]`（宏 `[l][r]`，见 `hblue_macro.ks` 定义）／`[p]`（ページ送り）
- **框内换行**：`[l]`（宏 `lr` 里就是 `[l][r]`）⇒ **合并**
- **页边界**：`[p]`（ページ）与 `[cm]`（メッセージクリア）
- **双版**：一页内 ≥2 次点击 ⇒ 先列段行（每次点击一行），再列合并行（整页一行）；单次点击的页只出一行
- **选项**：`[link storage=… target=…]` … `[endlink]` ＝ 一行一条，按出现位置入列
- **ruby**：`[ruby text="…"]` 只去掉标签、保留基字
- **名字**：全篇 **无 `[name]` 标签、无行首「名｢」前缀** ⇒ 无独立名字窗 ⇒ 不产出任何名字

用法：
  python scripts/kag3_ks.py --dir <ks 目录> --out 成品.txt [--raw raw目录] [--single]
"""
import argparse
import io
import os
import re
import sys

TAG = re.compile(r'\[[^\]\r\n]{0,120}\]')
LINK = re.compile(r'\[link\b[^\]]*\]', re.I)
WAIT = re.compile(r'(\[r\]|\[lr\]|\[p\])', re.I)
BREAK = re.compile(r'\[(?:p|cm)\b[^\]]*\]', re.I)
CTRL = re.compile(r'\[(?:r|lr|p|cm)\b[^\]]*\]', re.I)


def clean(s):
    # KAG 里脚本内的换行**不换行显示**（换行只由 `[l]` 之类控制）⇒ 一律折掉
    s = TAG.sub('', s).replace('\n', '').replace('\t', '')
    return s.strip('\u3000 ')


def _tokens(t):
    """扫描 `[tag]`：**尊重双引号**（`[eval exp=" … "]` 里可含换行与右括号）。产出 (kind, payload)。"""
    i, n, buf = 0, len(t), []
    while i < n:
        c = t[i]
        if c != '[':
            j = t.find('[', i)
            if j < 0:
                buf.append(('text', t[i:]))
                break
            buf.append(('text', t[i:j]))
            i = j
            continue
        j, q = i + 1, False
        while j < n:
            ch = t[j]
            if q:
                if ch == '"':
                    q = False
            elif ch == '"':
                q = True
            elif ch == ']':
                break
            elif ch == '[':
                break
            j += 1
        if j < n and t[j] == ']':
            buf.append(('tag', t[i + 1:j]))
            i = j + 1
        else:
            buf.append(('text', c))
            i += 1
    return buf


def parse(path, dual=True):
    raw = io.open(path, 'rb').read().decode('cp932', 'replace').replace('\r\n', '\n')
    keep = []
    for ln in raw.split('\n'):
        s2 = ln.strip()
        if not s2 or s2.startswith(';') or s2.startswith('*') or s2.startswith('@'):
            continue
        keep.append(ln)
    fixed = []
    for ln in keep:
        s3 = ln.rstrip()
        if s3 and s3.endswith(']') and not s3.lstrip().startswith('[') and re.match(r'[a-z_0-9]+\s', s3) and '=' in s3:
            s3 = '[' + s3          # 原文缺陷：命令少了左中括号（全篇 2 处）
        fixed.append(s3)
    toks = _tokens('\n'.join(fixed))

    out, buf, cur = [], [], []
    i = 0
    while i < len(toks):
        kind, v = toks[i]
        if kind == 'tag':
            nm = re.match(r'\s*([a-z_0-9]+)', v, re.I)
            nm = nm.group(1).lower() if nm else ''
            if nm == 'link':
                j, acc = i + 1, []
                while j < len(toks):
                    k2, v2 = toks[j]
                    m2 = re.match(r'\s*([a-z_0-9]+)', v2, re.I) if k2 == 'tag' else None
                    if m2 and m2.group(1).lower() == 'endlink':
                        break
                    if k2 == 'text':
                        acc.append(v2)
                    j += 1
                opt = clean(''.join(acc)).lstrip('・').strip()
                if opt:
                    out.append(('opt', opt))
                i = j + 1
                continue
        i += 1
        if kind == 'text':
            cur.append(v)
            continue
        name = re.match(r'\s*([a-z_0-9]+)', v, re.I)
        name = name.group(1).lower() if name else ''
        if name in ('r', 'lr', 'p', 'cm'):
            txt = clean(''.join(cur))
            cur = []
            if txt:
                buf.append(txt)
            if name in ('p', 'cm') and buf:
                # 单版＝每次点击一行；双版再补一条「整页合并行」（仅当本页 ≥2 次点击）
                out.extend(('line', x) for x in buf)
                if dual and len(buf) >= 2:
                    out.append(('line', ''.join(buf)))
                buf = []
    txt = clean(''.join(cur))
    if txt:
        buf.append(txt)
    if buf:
        out.extend(('line', x) for x in buf)
        if dual and len(buf) >= 2:
            out.append(('line', ''.join(buf)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True)
    ap.add_argument('--out')
    ap.add_argument('--raw')
    ap.add_argument('--single', action='store_true', help='只出段行（不出合并行）')
    ap.add_argument('--order', help='文件顺序（逗号分隔，不含 .ks）')
    a = ap.parse_args()

    # 非正文 cast（TJS 插件 / 宏定义 / 菜单 / 标题 / 画面缩放）不参与
    SKIP = {'gvolume.ks', 'hblue_macro.ks', 'omake_menu.ks', 'first.ks', 'zoom.ks'}
    files = [f for f in os.listdir(a.dir) if f.lower().endswith('.ks') and f not in SKIP]
    if a.order:
        order = [x.strip() for x in a.order.split(',')]
        files = [f for f in files if f[:-3] in order]
        files.sort(key=lambda f: order.index(f[:-3]))
    else:
        files.sort()

    rows, stat = [], {}
    for f in files:
        got = parse(os.path.join(a.dir, f), dual=not a.single)
        n0 = len(rows)
        rows.extend(got)
        stat[f] = len(rows) - n0
        print('%-16s %5d' % (f, stat[f]), file=sys.stderr)
        if a.raw:
            os.makedirs(a.raw, exist_ok=True)
            with io.open(os.path.join(a.raw, f + '.tsv'), 'w', encoding='utf-8', newline='\n') as w:
                for k, v in got:
                    w.write('%s\t%s\n' % (k, v))

    if not a.out:
        return
    # 只有中黑点「・」的行＝选项 bullet 残留（不是文字）⇒ 不收
    rows = [(k, v) for k, v in rows if v.strip('・\u3000 ') != '']
    with io.open(a.out, 'w', encoding='utf-8-sig', newline='\n') as w:
        for k, v in rows:
            w.write(v + '\n')
    L = sorted(len(v) for _, v in rows)
    print('合计 %d 行 / 最长 %d / 中位 %d → %s' % (len(rows), L[-1], L[len(L) // 2], a.out), file=sys.stderr)


if __name__ == '__main__':
    main()
