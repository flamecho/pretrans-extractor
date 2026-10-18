#!/usr/bin/env python3
"""lint_docs.py —— 手册对账：**断链 / 孤儿册 / 空册 / 超限**。

为什么有它：手册是「按需只读一册」的结构，一旦某个指针指向已改名/已删除的册，
或者某册写完却没人引用（下次永远读不到），手册就会越用越钝。人肉检查不可靠。

检查项:
  A 断链      md 里 `` `NN-xxx.md` `` / `engines/<slug>.md` / `pitfalls/X.md` 指向不存在的文件
              （`engines/` `engines-N.md` 属**构建期注入**：工作版没有该目录 ⇒ 不计断链，
                发行版有 `references/engines/` ⇒ 严格校验。见 INJECTED）
  B 路由       引擎册是否在 `ENGINES*.md`（路由表）里被提到 —— 查「册写了但没人知道去哪找」
  C 孤儿册     references/ 下除 00-index / 00-triage 外，**没有任何文件引用**的册
  D 空/极薄册  < 200 B（多为写坏的占位或残留）
  E 超限       > 10 KB（SKILL.md 放宽到 12 KB）
  F 重复条目号 pitfalls 里同一编号（①/ⓨ/A12…）出现多次（可能是重复粘贴）

用法:
  python scripts/lint_docs.py                       # 默认查已安装 skill + 当前目录的 memory
  python scripts/lint_docs.py --skill <dir> --mem <dir> --quiet
退出码: 0 = 无 A/C/D 级问题; 1 = 有
"""
import argparse
import glob
import io
import os
import re
import sys

# 默认取「脚本所在目录的上一级」= 本包根目录（不依赖安装名，换机器也不会指错）
SKILL_DEF = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXEMPT = {'00-index.md', '00-triage.md', 'third-party.md'}
# ★ 构建期注入（2026-10-18）：`engines/` 与 `engines*.md` **只在发行版存在**
#   —— build_dist.py 从工作区记忆 `MEM/engines/*.md` 注入，工作版根本没有这个目录。
#   工作版里 00-triage 的同名指针属**预期缺失**，不该算断链：否则常驻 38 条噪声，
#   真断链会被淹掉（人会习惯性无视整个 A 项）。发行版（有 references/engines/）仍严格校验。
INJECTED = re.compile(r'^(?:engines/[A-Za-z0-9_.\-]+\.md|engines(?:-[0-9a-z]+)?\.md)$')


def read(p):
    with io.open(p, encoding='utf-8', errors='replace', newline='') as f:
        return f.read()


def collect(skill, mem):
    """→ (files: [(path, text)], refs: {basename: 引用次数})"""
    files = []
    for root, pats in ((skill, ['SKILL.md', 'references/*.md',
                                'references/pitfalls/*.md', 'references/engines/*.md']),
                       (mem, ['*.md', 'engines/*.md'])):
        for pat in pats:
            for p in glob.glob(os.path.join(root, pat)):
                if os.path.isfile(p) and not re.match(r'\d{4}-\d{2}-\d{2}\.md$', os.path.basename(p)):
                    files.append((p, read(p)))
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--skill', default=SKILL_DEF)
    ap.add_argument('--mem', default=os.path.join(os.getcwd(), '.workbuddy', 'memory'))
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()

    files = collect(a.skill, a.mem)
    skill_refs = os.path.join(a.skill, 'references')
    have = {}
    for p, _ in files:
        have.setdefault(os.path.basename(p), []).append(p)
    # references 下的相对路径集合（供 pitfalls/xx 判断）
    rel = {os.path.relpath(p, skill_refs).replace('\\', '/') for p, _ in files
           if os.path.abspath(p).startswith(os.path.abspath(skill_refs))}
    eng = set()
    for d in (os.path.join(a.mem, 'engines'), os.path.join(a.skill, 'references', 'engines')):
        if os.path.isdir(d):
            eng |= {f for f in os.listdir(d) if f.endswith('.md')}

    A, C, D, E, F = [], [], [], [], []
    used = {}
    eng_mention = set()
    inj = []                    # 构建期注入项（工作版预期缺失）
    # 是否发行版布局：references/engines/ 目录或 references/engines*.md 存在
    is_dist = (os.path.isdir(os.path.join(a.skill, 'references', 'engines'))
               or os.path.isfile(os.path.join(a.skill, 'references', 'engines.md')))

    def miss(base, m):
        """断链记账：命中构建期注入白名单且当前是工作版 ⇒ 记为预期缺失，不算断链。"""
        if not is_dist and INJECTED.match(m):
            inj.append((base, m))
        else:
            A.append((base, m))

    for p, t in files:
        base = os.path.basename(p)
        for m in set(re.findall(r'`([0-9]{2}[0-9a-z\-]*\.md)`', t)):
            if re.match(r'\d{4}-\d{2}-\d{2}\.md$', m):      # 日报引用：按日期取，不在索引集合内
                continue
            if m not in rel and m not in have:
                miss(base, m)
        for m in set(re.findall(r'`?(?:references/)?(pitfalls/[A-Za-z0-9\-]+\.md)`?', t)):
            if m not in rel and os.path.basename(m) not in have:
                miss(base, m)
            used[m] = used.get(m, 0) + 1
        for m in set(re.findall(r'engines/([A-Za-z0-9_.\-]+\.md)', t)):
            eng_mention.add(m)
            if m not in eng:
                miss(base, 'engines/' + m)
        # 路由续册（`engines-2.md` / `engines-solo.md`）同样只在发行版存在
        for m in set(re.findall(r'`(engines(?:-[0-9a-z]+)?\.md)`', t)):
            if m not in have and not os.path.isfile(os.path.join(skill_refs, m)):
                miss(base, m)
        # 引用计数（粗粒度：出现过就算）
        for other in list(rel) + list(eng):
            if other != base and other in t:
                used[other] = used.get(other, 0) + 1

        size = os.path.getsize(p)
        lim = 12 * 1024 if base == 'SKILL.md' else 10 * 1024
        if base.endswith('.md'):
            if size > lim:
                E.append((base, size))
            if size < 200 and 'engine' not in p:
                D.append((base, size))

    # C 孤儿册（references 下的阶段册，排除索引类）
    for r in sorted(rel):
        if r in EXEMPT or r.startswith('pitfalls/'):
            continue
        if used.get(r, 0) == 0 and os.path.basename(r) not in used:
            C.append(r)
    # B 路由缺失：引擎册没被任何 ENGINES*.md 提到
    eng_route = ''.join(t for p, t in files
                        if re.match(r'(?:ENGINES|engines)(?:-[0-9a-z]+)?\.md$',
                                    os.path.basename(p), re.I))
    B = sorted(e for e in eng if e not in eng_route and e not in eng_mention)

    # F pitfalls 编号重复（同一行首编号 ≥2 次）
    CIRC = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟㊱㊲㊳㊴㊵㊶㊷㊸㊹㊺㊻㊼㊽㊾㊿ⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩ'
    for p, t in files:
        if os.sep + 'pitfalls' + os.sep not in p:
            continue
        marks = re.findall(r'^\s*(?:#{1,3}\s*)?\*\*?([' + CIRC + r'])', t, re.M)
        dup = {c for c in marks if marks.count(c) > 1}
        if dup:
            F.append((os.path.basename(p), ''.join(sorted(dup))))

    # G 排版（影响 Markdown 渲染：围栏配对 / 表格列数 / 块前空行 / 行尾空格）
    G = []
    FENCE = re.compile(r'^\s*`{3,}')
    for p, t in files:
        base = os.path.basename(p)
        ls = t.split('\n')
        fs = [i + 1 for i, l in enumerate(ls) if FENCE.match(l)]
        if len(fs) % 2:
            G.append((base, '代码围栏 %d 个（未配对）' % len(fs)))
        in_f, tbl = False, []
        for i, l in enumerate(ls, 1):
            if FENCE.match(l):
                in_f = not in_f
                tbl = []
                continue
            if in_f:
                continue
            s = l.strip()
            pr = ls[i - 2].strip() if i >= 2 else ''
            if s and l != l.rstrip(' \t'):
                G.append((base, 'L%d 行尾多余空格' % i))
            if s.startswith('|') and pr and not pr.startswith('|'):
                G.append((base, 'L%d 表格前缺空行' % i))
            if re.match(r'^#{1,6} ', s) and pr and not pr.startswith('#'):
                G.append((base, 'L%d 标题前缺空行' % i))
            if s.startswith('|') and s.endswith('|'):
                tbl.append(len(re.split(r'(?<!\\)\|', s)) - 2)
            else:
                if len(tbl) >= 2 and len(set(tbl)) > 1:
                    G.append((base, 'L%d 表格列数不一 %s' % (i - len(tbl), sorted(set(tbl)))))
                tbl = []

    def show(title, rows, fmt=lambda r: '  ' + ' → '.join(str(x) for x in r)):
        if rows and not a.quiet:
            print('\n== %s（%d）==' % (title, len(rows)))
            for r in rows[:20]:
                print(fmt(r))
            if len(rows) > 20:
                print('  … 另有 %d 条' % (len(rows) - 20))

    show('A 断链', A)
    if inj and not a.quiet:
        print('\n== 构建期注入（%d）==' % len(inj))
        print('  工作版无 references/engines/ —— 这类指针由 build_dist.py 从工作区记忆注入，'
              '发行版才存在；已按预期缺失跳过，不算断链。')
    show('B 引擎册未进路由表', [(b,) for b in B], lambda r: '  ' + r[0])
    show('C 孤儿册（无人引用）', [(c,) for c in C], lambda r: '  ' + r[0])
    show('D 空/极薄册', D, lambda r: '  %s  %d B' % (r[0], r[1]))
    show('E 超限', [(x, s) for x, s in E], lambda r: '  %-28s %d B' % (r[0], r[1]))
    show('F 坑册编号重复', F, lambda r: '  %s  %s' % (r[0], r[1]))
    show('G 排版（渲染相关）', G, lambda r: '  %-30s %s' % (r[0], r[1]))

    print('\n--- 文件 %d ｜ 断链 %d ｜ 路由缺 %d ｜ 孤儿 %d ｜ 空册 %d ｜ 超限 %d ｜ 排版 %d ｜ 注入跳过 %d ---'
          % (len(files), len(A), len(B), len(C), len(D), len(E), len(G), len(inj)))
    bad = len(A) + len(C) + len(D) + len(G)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
