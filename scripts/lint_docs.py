#!/usr/bin/env python3
"""lint_docs.py —— 手册对账：**断链 / 孤儿册 / 空册 / 超限**。

为什么有它：手册是「按需只读一册」的结构，一旦某个指针指向已改名/已删除的册，
或者某册写完却没人引用（下次永远读不到），手册就会越用越钝。人肉检查不可靠。

检查项:
  A 断链      md 里 `` `NN-xxx.md` `` / `engines/<slug>.md` / `pitfalls/X.md` 指向不存在的文件
              （`engines/` `engines-N.md` 属**构建期注入**：工作版没有该目录 ⇒ 不计断链，
                发行版有 `references/engines/` ⇒ 严格校验。见 INJECTED）
  B 路由       引擎册是否在 `ENGINES*.md`（路由表）里被提到 —— 查「册写了但没人知道去哪找」
  C 孤儿册     references/ 下除 00-index / S0-triage 外，**没有任何文件引用**的册
  D 空/极薄册  < 200 B（多为写坏的占位或残留）
  F 小节编号   `## N.` 组号从 1 连续、`### N.M` 组内连续且父组存在（只看标题行）
  G 排版      围栏配对 / 表格列数 / 表格前空行 / 行尾空格（影响渲染）
  J 命令示例   `python scripts/X.py --flag` 里的脚本与参数是否真存在（只查发行版；不实跑）
  H §N 引用    拆分与重排后最容易失效的就是「见 §7」：
              · 带文件名（`xxx.md` §N）⇒ 目标册必须有该节（引擎册也查，它们有 §N 体系）
              · 裸 `§N` ⇒ 本册必须有该节；同行已点名某个 `.md` 的跳过（一句话列多节是合法的）

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
EXEMPT = {'00-index.md', 'S0-triage.md', 'third-party.md'}
# ★ 构建期注入（2026-10-18）：`engines/` 与 `engines*.md` **只在发行版存在**
#   —— build_dist.py 从工作区记忆 `MEM/engines/*.md` 注入，工作版根本没有这个目录。
#   工作版里 S0-triage 的同名指针属**预期缺失**，不该算断链：否则常驻 38 条噪声，
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

        # 体积不判（2026-10-26 取消硬线）：该不该拆只看「读者是否需要同时看这两段」。
        size = os.path.getsize(p)
        if base.endswith('.md') and size < 200 and 'engine' not in p:
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

    # F 小节编号（2026-10-28 改）：`## N.` 组号必须从 1 连续，`### N.M` 的组内序号必须连续、
    #   且父组必须存在。**只看标题行**，不数正文枚举（`- ① …` 这类列表项不算）。
    #   为什么不用圈码：全库已统一成 `## N.` / `### N.M`（圈码既不可跳转，也不能被 `§N` 引用）。
    #   小数插节（`## 0.5`）不参与校验——它是有意的「插在前面」，正则天然跳过。
    for p, t in files:
        base = os.path.basename(p)
        if not base.endswith('.md'):
            continue
        ls = t.split('\n')
        grps, subs = [], []
        for i, l in enumerate(ls, 1):
            mg = re.match(r'^## (\d+)\. ', l)
            ms = re.match(r'^### (\d+)\.(\d+) ', l)
            if mg:
                grps.append((i, int(mg.group(1))))
            elif ms:
                subs.append((i, int(ms.group(1)), int(ms.group(2))))
        if not grps and not subs:
            continue
        gv = [g for _, g in grps]
        # 两种合法起点：`§0` 是惯例（铁律/一句话）；**有意的续篇**从中间起（册头须写明），登记在册
        CONTINUATION = {
            'S4-unity-bytes-works.md',          # 主册 §1〜§6 讲引擎核心，本册从 §7 起讲逐作差异
            'hunex-ika-seq-arcanafamiglia.md',  # 与 hunex-ika-seq.md 共用编号（§7/§8 两作）
            'hunex-ika-seq-arcana2.md',         # 同上，§9 起
            'konami-unity-bytes-works.md',      # 主册 §1〜§7，本册从 §8 起
        }
        start = gv[0] if gv else 1
        if start not in (0, 1) and base not in CONTINUATION:
            F.append((base, '组号从 %d 起（应为 1；若是有意的续篇，须写进 CONTINUATION）' % start))
        elif gv != list(range(start, start + len(gv))):
            F.append((base, '组号不连续：%s' % gv))
        gset = set(gv)
        for gi in sorted(gset):
            v = [s for _, g, s in subs if g == gi]
            if v != list(range(1, len(v) + 1)):
                F.append((base, '组 %d 的条目号不连续：%s' % (gi, v)))
        for ln, gi, si in subs:
            if gi not in gset:
                F.append((base, 'L%d 子节 %d.%d 的父组 %d 不存在' % (ln, gi, si, gi)))

    # H §N 交叉引用（2026-10-27 加）：拆分/重排后最容易失效的就是「见 §7」这类指针。
    #   判据分两种：
    #     ① 写了文件名（`xxx.md` §N）→ 目标册必须有该节（引擎册也查，它们有 §N 体系）；
    #     ② 裸 `§N` → 本册必须有该节；本册无编号体系时不判（多为指 `SKILL.md §0`，已人工明确过）。
    #   「有编号体系」＝该册 ≥2 个 `## N.` 标题，否则 §N 引用本身就可疑。
    H = []
    secs, body = {}, {}
    for f, txt in files:                      # files 是 [(path, text)]
        if not f.endswith('.md'):
            continue
        body[os.path.basename(f)] = (f, txt)
        # 节号统一存成 float（`1.5` / `7.3` / `1` 都能比）——用 int 会在小数节号上崩
        secs[os.path.basename(f)] = {float(m.group(1)) for m in
                                     re.finditer(r'(?m)^#{2,3}\s+(\d+(?:\.\d+)?)\.?\s', txt)}
    for base, (f, txt) in body.items():
        # 报错文案里节号要显示成 `§1.5`／`§9`，不能是 float 的 `9.0`
        sv = lambda x: '%g' % x
        for m in re.finditer(r'§\s*(\d+(?:\.\d+)?)', txt):
            v = float(m.group(1))
            line = txt[:m.start()].count('\n') + 1     # 按字符位置数换行，不能对 split 后的列表切片
            whole = txt.split('\n')[line - 1]
            # ① 带文件名的引用
            # 注意：pre 里**不含** §（已被 m.start() 截掉），所以只能要求「以 .md 结尾」
            fm = re.search(r'([A-Za-z0-9_.\-]+)\.md`?\s*$', txt[max(0, m.start() - 60):m.start()])
            if fm:
                tgt = fm.group(1) + '.md'
                if tgt in secs and len(secs[tgt]) >= 2 and v not in secs[tgt]:
                    H.append((base, 'L%d → %s §%s 不存在' % (line, tgt, sv(v))))
                continue
            # ①b 纯前缀 + §N（`04` §2.6 / `references/05` §6）：前缀不是文件名，读者无法定位。
            if re.search(r'`(?:references/)?0[0-7]`\s*§', whole):
                msg = 'L%d 「`0X` §N」写法：前缀不是文件名，请写全 `xxx.md`' % line
                if (base, msg) not in H:      # 同一行出现多处只报一次
                    H.append((base, msg))
                continue
            # ② 裸 §N：本册有编号体系才判。**同一行里已点名某个 .md 就跳过**——
            #    「已下沉至 `xxx.md`（§7 …／§8 …）」这类一句话列多节是合法的，不该报。
            if re.search(r'[A-Za-z0-9_.\-]+\.md', whole):
                continue
            if len(secs.get(base, ())) >= 2 and v not in secs[base]:
                H.append((base, 'L%d 裸 §%s 不存在（本册有 %s）' %
                          (line, sv(v), ', '.join(sv(x) for x in sorted(secs[base])))))

    # J 命令示例可跑性（2026-10-27 加）：读者第一件事就是复制 README 里的命令。
    #   只查发行版布局（需要 scripts/ 在同一棵树下）：脚本存在 + 行内 `--flag` 确实出现在脚本源码里。
    #   不做「跑一遍」——很多提取器不看参数就直接执行主体，跑起来会写文件（踩过）。
    J = []
    scripts_dir = os.path.join(a.skill, 'scripts')
    if is_dist and os.path.isdir(scripts_dir):
        srcs = {}
        for f in os.listdir(scripts_dir):
            if f.endswith('.py'):
                srcs[f] = read(os.path.join(scripts_dir, f))
        # collect() 只取 SKILL.md 与 references/*，**不含根目录的 README / CHANGELOG**——
        # 而读者最先复制的恰恰是 README 里的命令（2026-10-27 实测漏掉 --fix 那条）。
        scan = dict(body)
        for n in ('README.md', 'CHANGELOG.md'):
            p2 = os.path.join(a.skill, n)
            if os.path.isfile(p2):
                scan[n] = (p2, read(p2))
        # `scripts/INDEX.md` 是工具手册本身（19 条命令），它不在 references/ 下所以 collect() 取不到
        p3 = os.path.join(scripts_dir, 'INDEX.md')
        if os.path.isfile(p3):
            scan['scripts/INDEX.md'] = (p3, read(p3))
        for base, (f, txt) in scan.items():
            for m in re.finditer(r'python\s+scripts/([A-Za-z0-9_]+\.py)([^\n`|]*)', txt):
                n, rest = m.group(1), m.group(2)
                ln = txt[:m.start()].count('\n') + 1
                # 占位符（`X.py` / `xxx.py`）是说明用的，不是真命令
                if n[:1] in ('X', 'x'):
                    continue
                if n not in srcs:
                    J.append((base, 'L%d 脚本不存在：%s' % (ln, n)))
                    continue
                for flag in sorted(set(re.findall(r'(--[a-z][a-z0-9\-]+)', rest))):
                    if flag not in srcs[n]:
                        J.append((base, 'L%d %s 不支持 %s' % (ln, n, flag)))

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
            # 标题长度：超过 100 字就不是标题了，是一段话（没法当目录扫）。
            # 判据只对 `## N.` / `### N.M` 编号标题生效——刻意的长标题（作品名 + 判据）不在此列。
            mt = re.match(r'^#{2,3} \d[\d.]* (.+)$', s)
            if mt and len(mt.group(1)) > 100:
                G.append((base, 'L%d 标题 %d 字（>100，细节应移到正文首段）' % (i, len(mt.group(1)))))
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
    show('F 小节编号', F, lambda r: '  %-30s %s' % (r[0], r[1]))
    show('H §N 引用失效', H, lambda r: '  %-30s %s' % (r[0], r[1]))
    show('J 命令示例不可跑', J, lambda r: '  %-30s %s' % (r[0], r[1]))
    show('G 排版（渲染相关）', G, lambda r: '  %-30s %s' % (r[0], r[1]))

    print('\n--- 文件 %d ｜ 断链 %d ｜ 路由缺 %d ｜ 孤儿 %d ｜ 空册 %d ｜ 排版 %d ｜ 注入跳过 %d ---'
          % (len(files), len(A), len(B), len(C), len(D), len(G), len(inj)))
    bad = len(A) + len(C) + len(D) + len(G)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
