#!/usr/bin/env python3
"""从解析报告生成作品、工具、日志片段及引擎文档建议。

python scripts/archive_work.py --report R.md
python scripts/archive_work.py --report R.md --apply
python scripts/archive_work.py --report R.md --apply --apply-log

--work/--name 指作品名；--main 指主角名。--rows、--engine、--platform 可覆盖报告字段。
片段保存到 _archive/<作品>/；仅自动生成片段默认允许覆盖，--force-frag 可覆盖手写片段。
作为库使用：infer(report_path) 返回 name/plat/fam/eng/rows/main/tools/keys。
退出码：0 成功；2 报告缺失或必填字段不全。"""
import argparse
import io
import os
import re
import sys
import time

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not os.path.isfile(os.path.join(SKILL_ROOT, 'SKILL.md')):
    SKILL_ROOT = os.path.expanduser('~/.workbuddy/skills/vn-custom-bytecode-text')

# 自动生成片段的首行标记（有无这个标记 = 「机器写的」还是「人写的」，据此决定 dry-run 要不要覆盖）
AUTO = '<!-- auto: archive_work.py（本文件由工具生成；手改过就删掉这行，之后不会被覆盖）-->\n'

FAM = [
    ('cdar', r'CDAR|コルダ|遥か|下天の華|pasc|Ruby Party|アンジェリーク|NeoRomance'),
    ('stcm2l', r'STCM2|Idea Factory|Otomate/I-F|IF系'),
    ('hunex', r'HuneX|Ogre|IKA|HFU2|HLZS|HESL|allscr|mrgd00|MZX0|Ogre系'),
    ('takuyo', r'Takuyo|gss|LSDARC|SCR ?2\.00|SCR ?1\.10'),
    ('konami', r'KONAMI|Girl\'s Side|\.bytes'),
    ('m2', r'ADVENGINE|M2|PSB|PGD'),
    ('mages', r'MAGES\.|MPK|SC3|5pb'),
    ('boys3', r'Boys3|Swallowtail'),
    ('nnn', r'System-NNN|NNNLib|\.spt'),
    ('unity', r'Unity|IL2CPP|Naninovel|assetbundle'),
    ('evb', r'\.evb|MARC|Otomate VM'),
]
PLAT = [('psv', r'PSV|PS Vita|PCSG'), ('psp', r'PSP|ULJM|ULJS|ULKS|NPJH'),
        ('ps2', r'PS2|PlayStation 2|SLPS|SLPM'), ('switch', r'Switch|NSW|NS-JP|XCI|NSP|TID `01'),
        ('pc', r'\bPC\b|Windows|RPG ?Maker|AdvHD|BGI|\.exe')]
LAB = {'psv': 'PSV', 'psp': 'PSP', 'ps2': 'PS2', 'switch': 'Switch', 'pc': 'PC', 'other': '其它'}

def read(p):
    with io.open(p, encoding='utf-8', errors='replace', newline='') as f:
        return f.read()


def pick(t, pats):
    for p in pats:
        m = re.search(p, t, re.M)
        if m:
            return m.group(1) if m.groups() else m.group(0)
    return ''


MAIN_STOP = {'主角', '主角名', '主人公', '主人公名', 'ヒロイン', '默认名', '可变名', '外部核对',
             '台词', '全部', '名字', '名字槽', '假名', '默认', '未记', '本作', '姓名', '主角名槽',
             '真名', '读音', '姓名槽', '名字输入', '输入值', '可变', '不明', '无', '同上'}
# 含这些片段的**一律不是人名**（技术词 / 说明语）
NAME_BAD = ('宏', '占位', '名札', '替换', '自检', '行首', '表内', '空串', '规范', '丢弃', '本作',
            '要点', '关键', 'すべて', '原文', '内联', '通关', '插入', '可变', '默认', '不明', '未记',
            '输入', '槽', '读取', '辨识', '说明', '规则', '名字', '姓名', '台词', '字幕', '名牌',
            '记录', '行为', '判断', '确认', '处理', '方式', '情形', '情况', '条目', '字段', '示例',
            '改名', '核对', '吻合', '提出', '用户', '全部', '主角的', '不可', '可以', '见报告', '未知',
            '主角名', '主人公名', '未出现', '分别', '两个', '三个', '以上', '以下', '多个',
            '未使用', '不适用', '无需', '待定', '参考', '攻略角色', '主要角色', '选项',
            '角色', '登场人物', '人物', '攻略对象', '顺序', '次序', '列表', '一览', '如下',
            '合计', '总计', '共', '若干')
JP = r'\u3040-\u30ff\u4e00-\u9fff\u3005\u30fc'
# 主角名：**锚定在关键词上**取（避免抓到「成品」「下記」这类片段）
NAME_OK = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff\u3005\u30fc\s・＝=]{2,20}')
KW = r'(?:主角名?|主人公|ヒロイン)'
ANCHORED = [
    KW + r'\s*\|\s*([^\n|]+)',                                   # 表格 | 主人公 | X |
    KW + r'\s*(?:の)?(?:名|名前|名称)?\s*[＝=]\s*([^\n]{2,20})',   # 主角＝X
    KW + r'\s*(?:の)?(?:名|名前)?\s*[（(]\s*([^）)]{2,20})',       # 主角名（X）
    KW + r'\s*(?:の)?(?:名|名前)?\s*[：:]\s*([^\n]{2,20})',        # 主角名：X
    KW + r'[^\n]{0,12}→\s*\**\s*([^\n|]{2,20})',                  # 主角名 → **X**
    r'([^\n（(]{2,20})\s*[（(]\s*' + KW + r'\s*[）)]',              # X（主角）
]
NEXT_HINT = re.compile(r'^#{1,6}\s|名\s*$|名[（(]|核对|默认')


def _clean_name(s):
    s = re.sub(r'\*+', '', s)
    s = re.sub(r'[「」『』〔〕\[\]]', '', s)
    s = re.split(r'[（(、,，。；;｜|/→]', s)[0]
    s = re.sub(r'\s+', ' ', s).strip(' ・＝=—–-')
    s = re.sub(r'^(?:主角|主人公|ヒロイン)\s*(?:の)?(?:名|名前|名称)?\s*[＝=：:]\s*', '', s)
    if any(b in s for b in NAME_BAD) or s in MAIN_STOP:
        return ''
    t = s.replace(' ', '')
    if not (2 <= len(t) <= 12) or not NAME_OK.fullmatch(s):
        return ''
    # 结构判据（挡句子片段）：有空格「姓 名」／≤4 字／纯片假名
    kata = all('\u30a1' <= ch <= '\u30fa' or ch == 'ー' for ch in t)
    if not (' ' in s or len(t) <= 4 or kata):
        return ''
    return s.strip()


def _leading_name(line):
    """标题/说明的**下一行**常直接以名字开头（`### 主角默认名` → `月嶋 ヒカリ`）。"""
    s = re.sub(r'^[\s>\-*|]+', '', line)
    m = re.match(r'([\u3040-\u30ff\u4e00-\u9fff\u3005\u30fc][^\s、,，。：:｜|]{0,10}(?:\s[\u3040-\u30ff\u4e00-\u9fff\u3005\u30fc]{1,8})?)', s)
    return _clean_name(m.group(1)) if m else ''


def find_main(t):
    """主角名：锚定关键词取候选 → 按「全文出现次数」择优（噪声天然淘汰）。"""
    lines = t.split('\n')
    cands = []
    for i, l in enumerate(lines):
        if not re.search(KW, l):
            continue
        got = False
        for pat in ANCHORED:
            m = re.search(pat, l)
            if m:
                v = _clean_name(m.group(1))
                if v:
                    cands.append(v)
                    got = True
                    break
        if not got and NEXT_HINT.search(l):
            for nxt in lines[i + 1:i + 4]:
                if not nxt.strip():
                    continue
                v = _leading_name(nxt)
                if v:
                    cands.append(v)
                    break
        if len(cands) >= 8:
            break
    if not cands:
        return ''
    best, best_n = '', 0
    for c in cands:
        n = t.count(c)
        if n > best_n:
            best, best_n = c, n
    return best



FM_MAP = {'作品': '作品', 'title': '作品', '平台': '平台', 'platform': '平台', '引擎': '引擎',
          'engine': '引擎', '主角': '主角', 'main': '主角', '主人公': '主角',
          '行数': '行数', 'rows': '行数', '日期': '日期', 'date': '日期'}


def front_matter(t):
    """报告头部的机器可读块（可选）：
    ---
    作品: XXX
    平台: PSP
    引擎: STCM2L
    主角: 西村 あかり
    行数: 31,838
    ---
    有它 ⇒ 字段零歧义；没有 ⇒ 退回正则（结果标 `auto_main`）。"""
    m = re.match(r'^\ufeff?---\s*\n(.*?)\n---\s*\n', t, re.S)
    if not m:
        return {}
    d = {}
    for line in m.group(1).split('\n'):
        if ':' not in line and '：' not in line:
            continue
        k, v = re.split(r'\s*[:：]\s*', line, maxsplit=1)
        k = k.strip().strip('-').strip()
        if k in FM_MAP:
            d[FM_MAP[k]] = v.strip().strip('"\'')
    return d


def infer(report, name='', plat_='', engine='', rows_='', main_=''):
    """**纯字段推断**（不写任何文件）。main() 与批量评估共用。

    优先级：**front-matter（推荐，零歧义）** > 正则兜底（会标 `_auto=True` 供人工核对）。
    """
    t = read(report)
    fm = front_matter(t)

    name = name or fm.get('作品') or fm.get('title') or pick(t, [r'^#\s*《?([^》\n（(]+)', r'^#\s*(.+)'])
    name = re.sub(r'\s*[—\-–·]?\s*(?:全文本提取\s*[·•]?\s*)?解析报告\s*$', '', name or '').strip()
    name = re.sub(r'^\[[^\]]*\]\s*', '', name).strip('《》 ')

    plat = (plat_ or fm.get('平台') or '').lower()
    if plat not in LAB:
        plat = 'other'
        for k, pat in PLAT:
            if re.search(pat, t[:2500]):
                plat = k
                break

    fam = ''
    for f, pat in FAM:
        if re.search(pat, engine or fm.get('引擎') or t[:3000], re.I):
            fam = f
            break
    fam = fam or 'misc'

    rows = rows_ or fm.get('行数') or ''
    if not rows:
        # 优先「成品 / 全文本 / 交付」那一行；再退到加粗；最后才取首个（**不要 max**：
        # 报告里常有「全 37,310 行（含系统/UI）」这类更大数字，max 会选错）
        best = None
        for l in t.split('\n'):
            for m in re.finditer(r'([\d]{1,3}(?:,[\d]{3})+|(?<![\d,])\d{4,7})\s*行', l):
                v = m.group(1)
                score = 0
                if re.search(r'成品|全文本|交付|txt|输出', l):
                    score += 3
                if '**' in l[max(0, m.start() - 3):m.start()]:
                    score += 1
                if best is None or score > best[0]:
                    best = (score, v)
        if best:
            rows = best[1]

    mc = main_ or fm.get('主角') or find_main(t)
    auto_main = (not main_) and not fm.get('主角')      # 正则抽的 ⇒ 待人工核对

    tools = sorted(set(re.findall(r'(?:tools|scripts)/([\w.\-]+\.py)', t)))

    keys = []
    for l in t.split('\n'):
        s = l.strip()
        if re.match(r'^[\s>\-*]*[⚠★]', s) and len(s) > 20:
            b = re.sub(r'^[\s>\-*]+', '', s)
            b = re.sub(r'^\*\*', '', b)
            keys.append(b[:150].rstrip('，,；;　 '))
        if len(keys) >= 6:
            break

    return dict(report=report, name=name, plat=plat, fam=fam,
                eng=engine or fm.get('引擎') or '', rows=rows, main=mc,
                tools=tools, keys=keys, auto_main=auto_main,
                fm=bool(fm.get('作品') or fm.get('主角') or fm.get('行数')))


def pick_book(mem, prefix, fam, plat, eng=''):
    # 引擎专属分册优先（族太粗时会走错册）：{plat} 会被替换
    SUBBOOK = [(r'NScripter', 'WORKS-misc-{plat}-ns.md')]
    if prefix == 'WORKS':
        for pat, tpl in SUBBOOK:
            c = tpl.format(plat=plat)
            if eng and re.search(pat, eng, re.I) and os.path.isfile(os.path.join(mem, c)):
                return c, os.path.join(mem, c)
        cands = ['WORKS-%s-%s.md' % (fam, plat), 'WORKS-%s.md' % fam,
                 'WORKS-misc-%s-1.md' % plat, 'WORKS-misc-%s.md' % plat,
                 'WORKS-misc-other.md']
    else:
        cands = ['TOOLS-works-%s-%s.md' % (fam, plat), 'TOOLS-works-%s.md' % fam,
                 'TOOLS-works-misc-%s.md' % plat, 'TOOLS-works-misc-other.md']
    for c in cands:
        p = os.path.join(mem, c)
        if os.path.isfile(p):
            return c, p
    return cands[0], os.path.join(mem, cands[0])


def fragments(d, stamp, mem=''):
    plat, name = d['plat'], d['name']
    tl = '、'.join('`scripts/%s`' % x for x in d['tools'][:6]) or '（见报告）'
    works = ['### %s' % name,
             '- **%s** · **%s** · **%s 行**' % (LAB.get(plat, plat), d['eng'] or ('%s 系' % d['fam']),
                                               d['rows'] or '未统计'),
             '- 主角：%s' % (d['main'] or '—（报告未记）')]
    if d['keys']:
        works.append('- 判据与差异：')
        works += ['  - %s' % k for k in d['keys']]
    if d['tools']:
        works.append('- 工具：' + tl)
    works.append('- 详见：`%s`｜日报 `%s`' % (os.path.basename(d['report']), stamp))

    tools_txt = ('### %s · %s\n- 工具：%s\n- 成品：%s 行\n- 详见：`%s` → `## %s`'
                 % (stamp, name, tl, d['rows'] or '未统计', os.path.basename(d['report']), name))

    log_txt = ('## %s（%s 行）\n\n- **平台/引擎**：%s · %s\n- **主角**：%s\n- **工具**：%s\n'
               '- **判据与差异**：\n%s\n- **报告**：`%s`'
               % (name, d['rows'] or '未统计', LAB.get(plat, plat), d['eng'] or d['fam'],
                  d['main'] or '—（未记）', tl,
                  '\n'.join('  - %s' % k for k in d['keys']) or '  - （见报告）',
                  os.path.basename(d['report'])))

    # 根据格式名称提示已有册；词元命中仅供人工复核。
    cands = []
    STOP = {'text', 'mode', 'other', 'works', 'bytes', 'script', 'table', 'engine',
            'lines', 'variant', 'alpha', 'beta', 'test', 'files', 'tools'}
    try:
        blob = read(d['report']).lower() if os.path.isfile(d['report']) else ''
        edir = os.path.join(SKILL_ROOT, 'references', 'engines')
        if blob and os.path.isdir(edir):
            for base, _, names in os.walk(edir):
                for fn in names:
                    if not fn.endswith('.md') or fn == 'index.md':
                        continue
                    slug = os.path.relpath(os.path.join(base, fn), edir)[:-3].replace(chr(92), '/')
                    hit = [t for t in re.split(r'[-/]', slug)
                           if len(t) >= 5 and t not in STOP and t in blob]
                    if hit:
                        cands.append((len(hit), slug))
            cands.sort(reverse=True)
    except Exception:
        cands = []
    tip = '`references/engines/index.md`（按签名与结构定位格式）'
    if cands:
        # 只留最高分（并列才并列）：低分命中多是报告里的通用英文词（extra/system/text）
        top = cands[0][0]
        best = [s for n, s in cands if n == top][:3]
        tip = '／'.join('`references/engines/%s.md`' % s for s in best) + '（候选，先核对签名与结构）'
    eng_txt = ('# 引擎册提示（%s）\n\n- 归族：`%s`\n- 建议册：%s\n'
               '- 格式册：只合并可复用的容器结构、解码与显示判据\n'
               '- 变体按签名、头布局和命令语法描述；单作参数、统计、姓名及状态写入已有报告或 WORKS'
               % (name, d['fam'], tip))

    return {'works.md': '\n'.join(works) + '\n', 'tools-works.md': tools_txt + '\n',
            'log.md': log_txt + '\n', 'engines.md': eng_txt + '\n'}


TEMPLATE = """---
作品: {name}
平台: PSP
引擎: 
主角: 
行数: 
日期: {date}
---

# {name}（PSP / ULJM-00000）全文本提取 —— 解析报告

> 头部 `---` 块由 `archive_work.py` 直接读取，用于生成索引；`行数` 会与成品实际行数比对。

## 1. 链路（可重跑）

```
① 解包：…
② 容器：…
③ 解密：…
④ 提取：python scripts/xxx_extract.py <输入> <输出>
```

## 2. 容器结论

| 文件 | 结论 |
|---|---|
|  |  |

## 3. 判据与差异（`⚠` / `★` 行会被 `distill.py` 优先收进沉淀草案）

- ★ 
- ⚠ 

## 4. 自检与外部核对

- `check_text.py`：PASS（E=0 / W=0）
- 主角名：`…` × N 次（vndb v…）
- 名札表 → vndb 逐个核对：通过

## 5. 重跑步骤

1. 依赖：…
2. 命令：…
3. 预期：N 行 / UTF-8 BOM / LF
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', help='解析报告；用 --template 时可省')
    ap.add_argument('--mem', default=os.path.join(os.getcwd(), '.workbuddy', 'memory'))
    ap.add_argument('--work', help='作品名（覆盖报告推断；一般不用给，报告文件名已能推出）')
    ap.add_argument('--name', help='[兼容旧调用] 同 --work＝**作品名**；'
                                  '⚠ 与 wrapup.py 的 --name（＝主角）不同义，别混用')
    ap.add_argument('--rows')
    ap.add_argument('--main', help='主角名（与 wrapup.py 的 --name 等价）')
    ap.add_argument('--engine')
    ap.add_argument('--platform')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--apply-log', action='store_true')
    ap.add_argument('--force-frag', action='store_true',
                    help='覆盖 _archive/<作品>/ 里手写过的片段（无自动标记的文件）')
    ap.add_argument('--template', nargs='?', const='', metavar='作品名',
                    help='输出报告骨架（含 front-matter）；给作品名则预填')
    ap.add_argument('--out', help='配合 --template：写到该文件（默认打印）')
    a = ap.parse_args()

    if a.template is not None:
        name = a.template.strip() or '<作品名>'
        tpl = TEMPLATE.format(name=name, date=time.strftime('%Y-%m-%d'))
        if a.out:
            os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
            with io.open(a.out, 'w', encoding='utf-8', newline='') as f:
                f.write(tpl)
            print('已写入:', a.out)
        else:
            print(tpl)
        return 0

    if not a.report or not os.path.isfile(a.report):
        print('[!!] 报告不存在：%s' % a.report)
        return 2
    if a.name and not a.work:
        # 2026-11-01 事故：把主角名「真」传给 --name ⇒ WORKS/TOOLS/日报全写成「真」、还多生出 _archive/真/
        print('[!] --name 在 archive_work 里是**作品名**（不是主角）；主角请用 --main。')
        print('    若要改作品名请显式用 --work；报告推断名＝%s'
              % os.path.basename(a.report).replace('_解析报告.md', ''))
    d = infer(a.report, a.work or a.name or '', a.platform or '', a.engine or '',
              a.rows or '', a.main or '')
    if not d['name']:
        print('[!!] 无法确定作品名，用 --name 指定')
        return 2

    stamp = time.strftime('%Y-%m-%d')
    fg = fragments(d, stamp, a.mem)
    works_name, works_path = pick_book(a.mem, 'WORKS', d['fam'], d['plat'], d['eng'])
    tools_name, tools_path = pick_book(a.mem, 'TOOLS-works', d['fam'], d['plat'], d['eng'])

    outdir = os.path.join(os.getcwd(), '_archive', re.sub(r'[\\/:*?"<>|]', '_', d['name']))
    os.makedirs(outdir, exist_ok=True)
    # 2026-11-01 事故：dry-run 也会写片段，把我手写好的 works.md/log.md 覆盖成骨架。
    # 规则：生成的片段带 AUTO 标记；目标文件存在且**没有**该标记 ⇒ 视为手写、跳过（--force-frag 才覆盖）。
    for fn, body in fg.items():
        dst = os.path.join(outdir, fn)
        body = AUTO + body
        if os.path.isfile(dst) and not a.force_frag:
            with io.open(dst, encoding='utf-8', errors='replace') as f:
                old = f.read(400)
            if AUTO not in old:
                print('[skip] 手写片段保留：%s（要覆盖加 --force-frag）' % fn)
                continue
        with io.open(dst, 'w', encoding='utf-8', newline='') as f:
            f.write(body)

    print('作品 : %s' % d['name'])
    print('平台 : %s   引擎族: %s   %s' % (LAB.get(d['plat'], d['plat']), d['fam'], d['eng']))
    print('行数 : %s   主角: %s%s' % (d['rows'] or '未统计', d['main'] or '—',
          '' if d['fm'] else '（正则抽取，请核对）'))
    print('工具 : %s' % ('、'.join(d['tools'][:6]) or '（未识别）'))
    print('判据 : %d 条' % len(d['keys']))
    print('落位 : WORKS → %s ｜ TOOLS → %s' % (works_name, tools_name))
    print('片段 : %s' % outdir)

    if a.apply:
        for path, key in ((works_path, 'works.md'), (tools_path, 'tools-works.md')):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            old = read(path) if os.path.isfile(path) else ''
            # 幂等：只要求「某个 ### 标题里含本作名」（标题可能带日期/括号/追記）
            if re.search(r'^###[^\n]*%s' % re.escape(d['name']), old, re.M):
                print('  [skip] %s 已有本作（%s）' % (os.path.basename(path), d['name']))
                continue
            with io.open(path, 'a', encoding='utf-8', newline='') as f:
                if old and not old.endswith('\n'):
                    f.write('\n')
                f.write('\n' + fg[key])
            print('  [ok] 追加 → %s' % os.path.basename(path))

    if a.apply_log:
        lp = os.path.join(a.mem, stamp + '.md')
        old = read(lp) if os.path.isfile(lp) else ''
        if ('## %s' % d['name']) in old:
            print('  [skip] 日报已有 `## %s`' % d['name'])
        else:
            with io.open(lp, 'a', encoding='utf-8', newline='') as f:
                f.write('\n' + fg['log.md'])
            print('  [ok] 追加 → %s' % os.path.basename(lp))

    if not a.apply:
        print('\n（未写入目标册；确认无误后加 --apply）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
