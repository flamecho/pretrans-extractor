#!/usr/bin/env python3
"""split_md.py —— **按语义边界**拆分 md（标题 / 编号条目），带零丢失校验与原子替换。

为什么有它：按字节数硬切会切在段落中间 ⇒ 分册无意义、条目断头、旧引用全失效
（2026-10-18 的返工就是这么来的）。本工具只在**自然边界**下刀。

认识哪些边界（`--unit` 可覆盖正则）：
  `## …` / `### …`          标题
  `**B22. …` / `**A12. …`   本库的条目式编号（最常见）
  `**①…` / `①…`             圈码条目
  `12. …`                   顶层有序列表

用法:
  python scripts/split_md.py references/S6-lines-options.md --dry-run
  python scripts/split_md.py references/S6-lines-options.md \
         --names "04-lines-options-a.md,04-lines-options-b.md"    # 语义命名（推荐）
  python scripts/split_md.py references --all --limit 10240       # 批量：只处理超限者

保证（任一不满足 ⇒ 不落盘）:
  1. 只在边界前切；单个条目自身超限才在**空行**处切，并插 `<!-- 续 k/m -->`。
  2. 正文行守恒：原文件每个非空行在新文件中出现次数不减（页头除外）。
  3. 边界守恒：原文件每条边界行的出现次数不减。
  4. 临时目录写入 → 校验 → 打印待删清单 → 断言与输出名不相交 → 才删旧、搬入。
退出码: 0 = 成功（含「无需拆」）; 2 = 校验失败或安全闸门拦下。
"""
import argparse
import os
import re
import shutil
import sys
from collections import Counter

# 自然边界
UNIT = re.compile(
    r'^(?:#{2,4}\s+\S'                     # 标题
    r'|\*\*[A-Z]{0,2}\d{1,3}[.．]\s'        # **B22. / **A12.
    r'|\*\*[①-⓿]'                           # **①
    r'|[①-⓿]'                               # ①
    r'|\d{1,2}\.\s+\S)')                    # 1. 顶层列表
H = re.compile(r'^(#{1,6})\s+(\S.*)$')
CAP_RESERVE = 300          # 每册页头预留


def read(p):
    with open(p, encoding='utf-8', newline='') as f:
        return f.read()


def write(p, s):
    os.makedirs(os.path.dirname(p) or '.', exist_ok=True)
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)


def size(s):
    return len(s.encode('utf-8'))


def units_of(lines, unit_re):
    """→ (preamble_lines, [ (start,end) ... ])  区间为 line 下标，左闭右开"""
    b = [i for i, l in enumerate(lines) if unit_re.match(l)]
    if not b:
        return lines, []
    pre = lines[:b[0]]
    spans = [(b[i], b[i + 1] if i + 1 < len(b) else len(lines)) for i in range(len(b))]
    return pre, spans


def para_split(block, cap, tag):
    """单条目超限：按空行切，插 `<!-- 续 k/m -->`"""
    paras, cur = [], []
    for l in block:
        if not l.strip():
            if cur:
                paras.append(cur)
                cur = []
        else:
            cur.append(l)
    if cur:
        paras.append(cur)
    chunks, cur, sz = [], [], CAP_RESERVE
    for p in paras:
        ps = size('\n'.join(p)) + 1
        if cur and sz + ps > cap:
            chunks.append(cur)
            cur, sz = [], CAP_RESERVE
        cur.append(p)
        sz += ps
    if cur:
        chunks.append(cur)
    out = []
    for i, c in enumerate(chunks, 1):
        body = [l for p in c for l in p] + ['']
        out.append(['<!-- %s 续 %d/%d -->' % (tag, i, len(chunks))] + body)
    return out


def dp_pack(blocks, cap):
    """blocks = [ [line,...] ]；求「册数最少 + 各册最均衡」的切法（避免末册只剩 1 KB）。"""
    n = len(blocks)
    sz = [size('\n'.join(b)) + 1 for b in blocks]
    pre = [0]
    for x in sz:
        pre.append(pre[-1] + x)
    budget = cap - CAP_RESERVE
    if pre[-1] <= budget:
        return [list(range(n))]
    INF = float('inf')
    for k in range(1, n + 1):
        f = [[INF] * (n + 1) for _ in range(k + 1)]
        cut = [[0] * (n + 1) for _ in range(k + 1)]
        f[0][0] = 0
        for kk in range(1, k + 1):
            for i in range(1, n + 1):
                for j in range(kk - 1, i):
                    v = max(f[kk - 1][j], pre[i] - pre[j])
                    if v < f[kk][i]:
                        f[kk][i] = v
                        cut[kk][i] = j
        if f[k][n] <= budget:
            parts, i = [], n
            for kk in range(k, 0, -1):
                j = cut[kk][i]
                parts.append(list(range(j, i)))
                i = j
            return list(reversed(parts))
    # 兜底：单块超限 ⇒ 逐块切
    parts, cur, s = [], [], 0
    for i, x in enumerate(sz):
        if cur and s + x > budget:
            parts.append(cur)
            cur, s = [], 0
        cur.append(i)
        s += x
    if cur:
        parts.append(cur)
    return parts


def pack(lines, spans, cap):
    blocks = []
    for (s, e) in spans:
        n = size('\n'.join(lines[s:e])) + 1
        if n > cap - CAP_RESERVE:
            for chunk in para_split(lines[s:e], cap, '续'):
                blocks.append(chunk)
        else:
            blocks.append(lines[s:e])
    return [[l for i in grp for l in blocks[i]] for grp in dp_pack(blocks, cap)]


def first_unit(vol):
    for l in vol:
        if UNIT.match(l):
            return re.sub(r'\*\*|^#+\s*', '', l).strip()[:46]
    return '(无标题)'


def verify(src_nonempty, outs, n_bounds, unit_re):
    err = []
    got = Counter()
    for t in outs:
        for l in t.split('\n'):
            if l.strip():
                got[l.rstrip()] += 1
    miss = [(l, c, got.get(l, 0)) for l, c in src_nonempty.items() if got.get(l, 0) < c]
    if miss:
        err.append('正文行丢失 %d 种，例：%r' % (len(miss), [(m[0][:40], m[1], m[2]) for m in miss[:3]]))
    bnd = sum(1 for t in outs for l in t.split('\n') if unit_re.match(l))
    if bnd < n_bounds:
        err.append('边界行减量 %d → %d' % (n_bounds, bnd))
    return err


def do_one(path, a):
    src = read(path)
    base = os.path.basename(path)
    stem, ext = os.path.splitext(base)
    lines = src.split('\n')
    h1 = base
    for i, l in enumerate(lines):
        if l.startswith('# '):
            h1 = l[2:].strip()
            break
    if size(src) <= a.limit and not a.force:
        print('  [OK] %-34s %6d B ≤ %d' % (base, size(src), a.limit))
        return 0
    unit_re = re.compile(a.unit) if a.unit else UNIT
    pre, spans = units_of(lines, unit_re)
    if len(spans) < 2:
        print('  [!!] %-34s 找不到 ≥2 个自然边界 ⇒ 需人工分节（不硬切）' % base)
        return 2
    vols = pack(lines, spans, a.limit)
    n = len(vols)
    if n == 1:
        print('  [!!] %-34s 边界太少/单条过大 ⇒ 需人工分节' % base)
        return 2
    if a.names:
        names = [x.strip() for x in a.names.split(',') if x.strip()]
        # ⚠ --names 若漏写扩展名，会写出无扩展名的文件并把旧册删掉（2026-10-19 実例：
        #   `--names "WORKS-misc-psp-2,WORKS-misc-psp-3"` → 两个无 .md 文件）⇒ 一律补回原扩展名
        names = [nm if nm.endswith(ext) else nm + ext for nm in names]
        if len(names) != n:
            print('  [!!] --names 给了 %d 个，实际需要 %d 个；切点：' % (len(names), n))
            for i, v in enumerate(vols, 1):
                print('        %d) %s' % (i, first_unit(v)))
            return 2
    else:
        names = ['%s-%d%s' % (stem, i, ext) for i in range(1, n + 1)]

    # 组装：页头 + 首册带原 preamble（去掉原 H1）+ 正文
    nav = a.nav or '00-index.md'
    outs = []
    for i, v in enumerate(vols, 1):
        hdr = ['# %s%s' % (h1, '（%d/%d）' % (i, n) if n > 1 else ''), '',
               '> 本册 %d 条：%s' % (sum(1 for l in v if unit_re.match(l)), first_unit(v)),
               '> 由 `%s` 按语义边界拆分（原文逐字保留、除页头外无改写）；导航见 `%s`。'
               % (base, nav), '']
        body = list(v)
        if i == 1 and pre:
            # preamble 去掉重复 H1，接在页头说明之后
            p = [l for l in pre if not l.startswith('# ')]
            while p and not p[0].strip():
                p.pop(0)
            body = p + ([''] if p else []) + body
        outs.append('\n'.join(hdr + body).rstrip('\n') + '\n')

    src_nonempty = Counter(l.rstrip() for l in lines if l.strip() and not l.startswith('# '))
    n_bounds = sum(1 for l in lines if unit_re.match(l))
    errs = verify(src_nonempty, outs, n_bounds, unit_re)
    print('  切点（%d 册）:' % n)
    for i, v in enumerate(vols, 1):
        print('    %d) %-30s %6d B  %s' % (i, names[i - 1], size(outs[i - 1]), first_unit(v)))
    if errs:
        print('  [FAIL] 校验未通过，未落盘：')
        for e in errs:
            print('    -', e)
        return 2
    print('  校验: 正文行守恒 / 边界守恒 → 通过')
    if a.dry_run:
        print('  [dry-run] 未写文件。')
        return 0

    d = os.path.dirname(os.path.abspath(path))
    tmp = os.path.join(d, '.split_tmp_%s' % stem)
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp)
    for nm, t in zip(names, outs):
        write(os.path.join(tmp, nm), t)
    olds = [f for f in os.listdir(d)
            if re.match(r'^%s([-_].*)?%s$' % (re.escape(stem), re.escape(ext)), f)
            and f not in names]
    inter = set(olds) & set(names)
    assert not inter, '安全闸门：待删清单与输出名相交 %s' % inter
    print('  待删旧册（%d）: %s' % (len(olds), ', '.join(olds) if olds else '无'))
    for f in olds:
        os.remove(os.path.join(d, f))
    for nm in names:
        shutil.move(os.path.join(tmp, nm), os.path.join(d, nm))
    os.rmdir(tmp)
    print('  [OK] 已写入: %s' % ', '.join(names))
    if n > 1 and not a.names:
        print('  ⚠ 用了 -1/-2 命名；建议 --names 改成有意义的册名（内容已按边界切好，改名不会再校验）。')
    print('  ⚠ 改引用：grep -rn "%s" .' % stem)
    return 0


def main():
    ap = argparse.ArgumentParser(description='按语义边界拆分 md（安全、可校验）')
    ap.add_argument('path', help='md 文件，或目录（配 --all）')
    ap.add_argument('--limit', type=int, default=10240)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--names', help='逗号分隔的新册名，数量须与切点一致')
    ap.add_argument('--nav', help='导航文件名（默认 00-index.md）')
    ap.add_argument('--unit', help='自定义边界正则')
    ap.add_argument('--all', action='store_true')
    a = ap.parse_args()
    if a.all:
        rc = 0
        for f in sorted(os.listdir(a.path)):
            p = os.path.join(a.path, f)
            if f.endswith('.md') and os.path.getsize(p) > a.limit:
                rc |= do_one(p, a)
        print('\n--- %s ---' % ('有文件需处理' if rc else '全部达标'))
        return rc
    return do_one(a.path, a)


if __name__ == '__main__':
    sys.exit(main())
