#!/usr/bin/env python3
"""distill.py —— 解析报告 → **沉淀草案**（分类 / 查重 / 建议落位），不改动 skill。

为什么有它：沉淀慢的根因不是「写」，而是**不知道该写哪、以及是不是已经写过**。
每次都要把 skill 重读一遍 ⇒ 30~60 分钟。本工具把这两件事变成机器判定：

  ① 抽候选：报告/日报里带 `⚠ ★ ※ 判据 坑 注意 必须 不能 禁止 误 差异 特例 ≠` 的行
  ② 查重：对 skill(`references/` + `pitfalls/`) 与 `memory/engines/` 做 4-gram 包含度比对
           ≥ 阈值 ⇒ 判「已覆盖」，只列出处，不再重写
  ③ 分类：按关键词映射到**真实存在**的目标册（`01-*`〜`06-*` / `pitfalls/*` / `engines/`）
  ④ 输出草案：待沉淀（勾选框 + 建议落位）/ 单作特例 / 已覆盖，写 `<out>`，skill 一字不动

用法:
  python scripts/distill.py --report "提取结果/解析报告/XX_解析报告.md"
  python scripts/distill.py --report R.md --log `references/`2026-10-18.md --open
  python scripts/distill.py --report R.md --skill <skill 目录> --mem <memory 目录> --out /tmp/d.md

退出码: 0 = 无待沉淀; 1 = 有待沉淀（提示人工处理）
"""
import argparse
import io
import os
import re
import sys
from collections import Counter, defaultdict

# 默认取「脚本所在目录的上一级」= 本包根目录（不依赖安装名，换机器也不会指错）
SKILL_DEF = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM_DEF = os.path.join(os.getcwd(), '.workbuddy', 'memory')

MARK = re.compile(r'^[\s>\-*]*(\*\*)?[⚠★※◆●▲]|⚠|★|※')
KW = re.compile(r'判据|坑|注意|必须|不能|不要|禁止|误|差异|特例|例外|≠|反过来|反例|陷阱|漏|错')
STRIP = re.compile(r'^[\s>\-*•]+|^\d+[.)]\s*|\*\*')

# 目标册：**只列 references/ 下真实存在的文件**（启动时会校验，缺的自动跳过）
SLOT = [
    (r'zRIF|psvpfsparser|header signature|PFS|pfs0dir', '01-psv-pfs.md'),
    (r'EBOOT|~PSP|self2elf|MIPS|PRX|BOOT\.BIN|kirk', '01-psp-eboot.md'),
    (r'hactool|titlekey|NCA|BKTR|prod\.keys|XCI|NSP', '01-switch-nca.md'),
    (r'CHD|chdman|zstd|hunk', '01-image-chd.md'),
    (r'主角名|主人公|一人称|称呼宏|人名宏|FFE6|FFE7|FF08|name\.|f\.family|改名', '03-names-macro.md'),
    (r'XOR|CRILAYLA|zlib|LZSS|LZ4|解压|解密|密钥|码表基址|替换槽|PUA|cp932|CP932|字形|字体|gaiji', '03-basics.md'),
    (r'ELF.*(码表|code)|code→Unicode|分区错位', '03-codetable-elf.md'),
    (r'位图字体|自建字体|GXT|G1T|renderfont|字形图集', '03-selffont.md'),
    (r'AFS|CPK|归档|块单位|定长表|索引表|偏移', '03-archive.md'),
    (r'STCM2', '02-stcm2l.md'),
    (r'opcode|指令|记录|标签|脚本结构|msgid|分支码', '02-structure.md'),
    (r'Unity|IL2CPP|Naninovel|assetbundle|\.bytes', '02-unity.md'),
    (r'名札|话者|说话人|续行|换框|成行|一次点击|选项|合并|折行|引号', '04-lines.md'),
    (r'用語辞典|辞典|豆知識|glossary', '04-lines-options.md'),
    (r'自检|品检|check_text|占位符|报告', '05-selfcheck.md'),
    (r'vndb|外部核对|核对', '05-external-report.md'),
    (r'串数|闭合|漏收|完整性', '05-completeness.md'),
    (r'清理|工作区|记忆|上下文|agent|memo|日志', '06-workspace.md'),
]


# 阶段册 → 坑册（同一条结论常常「阶段册讲怎么做、坑册讲别踩什么」）
PIT = {
    '01-psv-pfs.md': 'pitfalls/A1-decode-core.md',
    '01-psp-eboot.md': 'pitfalls/A1-decode-core.md',
    '01-switch-nca.md': 'pitfalls/A1-decode-core.md',
    '01-image-chd.md': 'pitfalls/A1-decode-core.md',
    '03-basics.md': 'pitfalls/A1-decode-core.md',
    '03-names-macro.md': 'pitfalls/C1-deliver.md',
    '03-codetable-elf.md': 'pitfalls/A2-decode-late.md',
    '03-selffont.md': 'pitfalls/B1-lines.md',
    '03-archive.md': 'pitfalls/A2-decode-late.md',
    '02-stcm2l.md': 'pitfalls/B2-tags-resume.md',
    '02-structure.md': 'pitfalls/A1-decode-core.md',
    '02-unity.md': 'pitfalls/A1-decode-core.md',
    '04-lines.md': 'pitfalls/B1-lines.md',
    '04-lines-options.md': 'pitfalls/B9-late-6.md',
    '05-selfcheck.md': 'pitfalls/C1-deliver.md',
    '05-external-report.md': 'pitfalls/C1-deliver.md',
    '05-completeness.md': 'pitfalls/C1-deliver.md',
    '06-workspace.md': 'pitfalls/C2-deliver-2.md',
}


ENGINE_HINT = re.compile(r'本作|本作特|该作|这部|仅此作|仅本作|只在本作')


def read(p):
    with io.open(p, encoding='utf-8', errors='replace', newline='') as f:
        return f.read()


def norm(s):
    s = re.sub(r'\s+', '', s)
    s = re.sub(r'[`*_>]', '', s)
    return s


def grams(s, n=4):
    s = norm(s)
    return {s[i:i + n] for i in range(max(0, len(s) - n + 1))} if len(s) >= n else {s}


def load_corpus(skill, mem):
    """→ (paras: list[(file, text)], index: gram->set(pid))"""
    files = []
    for root, pats in ((skill, ['references/*.md', 'references/pitfalls/*.md']),
                       (mem, ['engines/*.md', 'ENGINES*.md'])):
        for pat in pats:
            import glob
            files += [f for f in glob.glob(os.path.join(root, pat)) if os.path.isfile(f)]
    paras = []
    for f in files:
        t = read(f)
        for block in re.split(r'\n{2,}', t):
            b = block.strip()
            if len(norm(b)) >= 12:
                paras.append((os.path.basename(f), b))
    idx = defaultdict(set)
    for i, (_, b) in enumerate(paras):
        for g in grams(b):
            idx[g].add(i)
    return paras, idx, len(files)


def coverage(line, paras, idx, thr):
    g = grams(line)
    if not g:
        return 0.0, ''
    cnt = Counter()
    for x in g:
        for pid in idx.get(x, ()):
            cnt[pid] += 1
    if not cnt:
        return 0.0, ''
    pid, hit = cnt.most_common(1)[0]
    return hit / len(g), paras[pid][0]


def candidates(text):
    lines = text.split('\n')
    out = []
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        i += 1
        if len(s) < 16 or s.startswith('```') or s.startswith('#'):
            continue
        if not (MARK.search(s) or KW.search(s)):
            continue
        # 续行合并：本行未收句、下一行是普通正文 ⇒ 接上（报告里长句常被折行）
        joined = s
        while (len(joined) < 400
               and not re.search(r'[。．.!?！？」』）)】]\s*$', joined)
               and i < len(lines)):
            nxt = lines[i].strip()
            if (not nxt or nxt.startswith(('- ', '* ', '|', '#', '>', '```'))
                    or re.match(r'^\d+[.)]\s', nxt) or MARK.search(nxt)):
                break
            joined += nxt
            i += 1
        body = STRIP.sub('', joined).strip()
        if len(body) < 14:
            continue
        out.append((i, body))
    # 去重（归一化后前 30 字）
    seen, uniq = set(), []
    for i2, b in out:
        k = norm(b)[:30]
        if k in seen:
            continue
        seen.add(k)
        uniq.append((i2, b))
    return uniq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', required=True)
    ap.add_argument('--log', action='append', default=[], help='可多次给：补充日报')
    ap.add_argument('--skill', default=SKILL_DEF)
    ap.add_argument('--mem', default=MEM_DEF)
    ap.add_argument('--out')
    ap.add_argument('--thr', type=float, default=0.55, help='判定「已覆盖」的 4-gram 包含度阈值')
    a = ap.parse_args()

    src_all = [(os.path.basename(a.report), read(a.report))]
    for lg in a.log:
        if os.path.isfile(lg):
            src_all.append((os.path.basename(lg), read(lg)))
    paras, idx, nfile = load_corpus(a.skill, a.mem)

    have = set()
    ref_root = os.path.join(a.skill, 'references')
    for root, _, fs in os.walk(ref_root):
        for f in fs:
            if f.endswith('.md'):
                have.add(f)

    items = []
    for srcname, text in src_all:
        for ln, body in candidates(text):
            slot = ''
            for pat, f in SLOT:
                if re.search(pat, body):
                    if f in have:
                        slot = f
                        break
            cov, where = coverage(body, paras, idx, a.thr)
            items.append(dict(src=srcname, ln=ln, body=body, slot=slot or '',
                              cov=cov, where=where,
                              local=bool(ENGINE_HINT.search(body))))

    todo = [x for x in items if x['cov'] < a.thr and not x['local']]
    local = [x for x in items if x['cov'] < a.thr and x['local']]
    done = [x for x in items if x['cov'] >= a.thr]

    out = []
    title = re.sub(r'_解析报告\.md$|\.md$', '', os.path.basename(a.report))
    out.append('# 沉淀草案 · %s\n' % title)
    out.append('> 生成：`distill.py`（skill 语料 %d 册）。**本文件只是草案，skill 未被改动。**' % nfile)
    out.append('> 判定：4-gram 包含度 ≥ %.2f ⇒ 已覆盖；`本作/该作/仅此作` ⇒ 单作特例。\n' % a.thr)
    out.append('| 候选 | 待沉淀 | 单作特例 | 已覆盖 |')
    out.append('|---|---|---|---|')
    out.append('| %d | **%d** | %d | %d |\n' % (len(items), len(todo), len(local), len(done)))

    out.append('## 1. 待沉淀（勾选后落位；`→` 是建议目标）\n')
    if not todo:
        out.append('_无。_\n')
    buck = defaultdict(list)
    for x in todo:
        buck[x['slot'] or '（未定/交人工判）'].append(x)
    for slot in sorted(buck):
        pit = PIT.get(slot)
        out.append('### → `%s`（%d 条）%s\n'
                   % (slot, len(buck[slot]),
                     ('　＋ 可同时补 `%s`' % pit)
                     if pit and os.path.isfile(os.path.join(ref_root, *pit.split('/'))) else ''))
        for x in buck[slot]:
            out.append('- [ ] %s' % x['body'][:400])
            out.append('  - 来源：`%s:%d`　最接近：`%s`（相似度 %.2f）' % (x['src'], x['ln'], x['where'], x['cov']))
        out.append('')

    out.append('## 2. 单作特例（只进 `WORKS` 作品块 / `engines/<slug>.md`，不进通用册）\n')
    if not local:
        out.append('_无。_\n')
    for x in local:
        out.append('- %s　（`%s:%d`）' % (x['body'][:300], x['src'], x['ln']))
    out.append('')

    out.append('## 3. 已覆盖（不重复写；仅列出处）\n')
    if not done:
        out.append('_无。_\n')
    for x in done[:80]:
        out.append('- %.2f `%s`　← %s' % (x['cov'], x['where'], x['body'][:90]))
    if len(done) > 80:
        out.append('- …（另有 %d 条）' % (len(done) - 80))
    out.append('')

    txt = '\n'.join(out) + '\n'
    dest = a.out or os.path.join(os.getcwd(), '_distill', re.sub(r'[\\/:*?"<>|]', '_', title) + '.md')
    os.makedirs(os.path.dirname(dest) or '.', exist_ok=True)
    with io.open(dest, 'w', encoding='utf-8', newline='') as f:
        f.write(txt)
    print('候选 %d ｜ 待沉淀 %d ｜ 单作特例 %d ｜ 已覆盖 %d'
          % (len(items), len(todo), len(local), len(done)))
    for slot in sorted(buck):
        print('   → %-34s %d 条' % (slot, len(buck[slot])))
    print('草案：%s' % dest)
    return 1 if todo else 0


if __name__ == '__main__':
    sys.exit(main())
