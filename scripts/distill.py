#!/usr/bin/env python3
"""从报告生成文档修订草案。

提取判据与差异，对技能 references 和工作区 WORKS 做 4-gram 包含度比对，
输出未覆盖内容、单作特例及建议路径。草案不直接修改技能。

python scripts/distill.py --report R.md --skill DIR --mem DIR --out draft.md
退出码：0 无待处理内容；1 有待处理内容。"""
import argparse
import io
import os
import re
import sys
from collections import Counter, defaultdict

SKILL_DEF = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not os.path.isfile(os.path.join(SKILL_DEF, 'SKILL.md')):
    SKILL_DEF = os.path.expanduser('~/.workbuddy/skills/vn-custom-bytecode-text')
MEM_DEF = os.path.join(os.getcwd(), '.workbuddy', 'memory')

MARK = re.compile(r'^[\s>\-*]*(\*\*)?[⚠★※◆●▲]|⚠|★|※')
KW = re.compile(r'判据|坑|注意|必须|不能|不要|禁止|误|差异|特例|例外|≠|反过来|反例|陷阱|漏|错')
STRIP = re.compile(r'^[\s>\-*•]+|^\d+[.)]\s*|\*\*')

# 目标册：**只列 references/ 下真实存在的文件**（启动时会校验，缺的自动跳过）
SLOT = [
    (r'Naninovel|PrintText|AddChoice', 'engines/naninovel.md'),
    (r'SN\.BIN|sn\.bin', 'engines/nis-cpk-snbin.md'),
    (r'XP3|KiriKiri|KAG|吉里吉里', 'engines/kirikiri.md'),
    (r'STCM2|UNI2', 'engines/stcm2l.md'),
    (r'IKA SEQ|HFU2|UFFA', 'engines/hunex-ika.md'),
    (r'Takuyo|LSDARC|\bgss\b', 'engines/takuyo-gss.md'),
    (r'LiveMaker|LMScript|TpWord', 'engines/livemaker.md'),
    (r'NScripter|NSAr', 'engines/nscripter.md'),
    (r'zRIF|psvpfsparser|header signature|PFS|pfs0dir', 'platforms/psv-pfs.md'),
    (r'EBOOT|~PSP|self2elf|MIPS|PRX|BOOT\.BIN|kirk', 'decode.md'),
    (r'hactool|titlekey|NCA|BKTR|prod\.keys|XCI|NSP', 'platforms/switch-nca.md'),
    (r'CHD|chdman|zstd|hunk', 'engines/images.md'),
    (r'M2|PSB|PGD|MDF|ADVENGINE', 'engines/m2-psb.md'),
    (r'主角名|主人公|一人称|称呼宏|人名宏|FFE6|FFE7|FF08|name\.|f\.family|改名', 'names-and-macros.md'),
    (r'XOR|CRILAYLA|zlib|LZSS|LZ4|解压|解密|密钥|码表基址|替换槽|PUA|cp932|CP932|字形|字体|gaiji', 'decode.md'),
    (r'ELF.*(码表|code)|code→Unicode|分区错位', 'decode.md'),
    (r'位图字体|自建字体|GXT|G1T|renderfont|字形图集', 'decode.md'),
    (r'AFS|CPK|归档|块单位|定长表|索引表|偏移', 'archives.md'),
    (r'STCM2', 'engines/stcm2l.md'),
    (r'opcode|指令|记录|标签|脚本结构|msgid|分支码', 'script-structure.md'),
    (r'Unity|IL2CPP|Naninovel|assetbundle|\.bytes', 'engines/unity.md'),
    (r'名札|话者|说话人|续行|换页|换框|成行|一次点击|选项|合并|折行|引号', 'layout.md'),
    (r'用語辞典|辞典|豆知識|glossary', 'layout.md'),
    (r'自检|品检|check_text|占位符|报告', 'verification.md'),
    (r'vndb|外部核对|核对', 'verification.md'),
    (r'串数|闭合|漏收|完整性', 'verification.md'),
    (r'清理|工作区|记忆|上下文|agent|memo|日志', 'workspace.md'),
]


# 流程册与格式案例的建议目标
CASES = {
    'platforms/psv-pfs.md': 'decode-cases.md',
    'platforms/switch-nca.md': 'decode-cases.md',
    'decode.md': 'decode-cases.md',
    'archives.md': 'decode-cases.md',
    'engines/stcm2l.md': 'script-cases.md',
    'script-structure.md': 'script-cases.md',
    'layout.md': 'layout-cases.md',
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
    for root, pats in ((skill, ['references/**/*.md']),
                       (mem, ['WORKS*.md'])):
        for pat in pats:
            import glob
            files += [f for f in glob.glob(os.path.join(root, pat), recursive=True) if os.path.isfile(f)]
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
                have.add(os.path.relpath(os.path.join(root, f), ref_root).replace(chr(92), '/'))

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
    out.append('> 引擎册只收共通结构、解码与显示判据；单作参数、统计和状态留在已有报告或 WORKS。')
    out.append('> 判定：4-gram 包含度 ≥ %.2f ⇒ 已覆盖；`本作/该作/仅此作` ⇒ 单作特例。\n' % a.thr)
    out.append('| 候选 | 待沉淀 | 单作特例 | 已覆盖 |')
    out.append('|---|---|---|---|')
    out.append('| %d | **%d** | %d | %d |\n' % (len(items), len(todo), len(local), len(done)))

    out.append('## 1. 待复核的格式知识（确认共通性后合并至建议册）\n')
    if not todo:
        out.append('_无。_\n')
    buck = defaultdict(list)
    for x in todo:
        buck[x['slot'] or '（未定/交人工判）'].append(x)
    for slot in sorted(buck):
        case = CASES.get(slot)
        out.append('### → `%s`（%d 条）%s\n'
                   % (slot, len(buck[slot]),
                     ('　（格式案例见 `%s`）' % case)
                     if case and os.path.isfile(os.path.join(ref_root, case)) else ''))
        for x in buck[slot]:
            out.append('- [ ] %s' % x['body'][:400])
            out.append('  - 来源：`%s:%d`　最接近：`%s`（相似度 %.2f）' % (x['src'], x['ln'], x['where'], x['cov']))
        out.append('')

    out.append('## 2. 单作特例（写入已有报告或 WORKS）\n')
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
