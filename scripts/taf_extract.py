# -*- coding: utf-8 -*-
"""[JP]Truth and False —— KiriKiri/KAG3 专用提取驱动

复用 ks_kag_text 的 L0 断框模型（[r]=合并 / [l]=段界 / plc/cm/ct/er=页界 / link=选项），
仅补充本作特有的「上屏文本」：
  1. [hatena] / [hatena name="'X'"]  —— 名字印在正文框内（无独立名字窗）⇒ 用【】括上接同行
       裸 [hatena] → 【？？？】（引擎默认上屏字）；name="'X'" → 【X】
  2. 名字宏（harumi→ハルミ / naru→ナルホド / miturugi→ミツルギ …）——
       宏体 [font face=name]<字面>[r] 或 [font face=name][emb exp="%name|'默认'"][r]
       ⇒ 字面即上屏名，用【】括上作为内联名
  3. 标点宏 i/ei/ii/eii/maru —— 上屏标点：（ ） ＜＜ ＞＞ 。
  4. 选项 link1 name="'X'" —— 选项文字在 name= 字面属性里（非变量），展开为 [link]X[endlink]

用法: python scripts/taf_extract.py <ks目录> <out.txt> [--files a.ks,b.ks ...] [--mode dual|page]
"""
import sys, os, re, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ks_kag_text as K


# ── 标点宏：上屏字 ──────────────────────────────────────────────
TAF_PUNCT = {'i': '（', 'ei': '）', 'ii': '＜＜', 'eii': '＞＞', 'maru': '。'}

# ── 纯演出/控制标签（无上屏文本）：与名字宏同处一行时，其两侧分隔空格会泄漏为前导/尾随空格，
#    故在 preprocess 阶段连同「至多一个相邻空格」一并剥除（日文无词间空格，剥除安全）。
#    注意不要包含结构标签（plc/cm/ct/er/l/r/p/np/link 等，由 parse 处理）。
TAF_PRES_TAGS = ['resetfont', 'resetstyle', 'deffont', 'nasie', 'kao', 'fadeinbgm1',
                 'fadeoutbgm2', 'se', 'Mes0', 'rubi', 'eitem', 'item', 'item1',
                 'freeimage', 'nasi', 'waku', 'blur', 'igin', 'igia', 'jkaisi1',
                 'jkaisi', 'yureoto', 'yure', 'flash', 'oni', 'kaisi', 'fimage',
                 'mappfont', 'move', 'matan', 'matam', 'mata', 'in', 'sysbtopt',
                 'ignore', 'endignore', 'kurae', 'wm', 'kie', 'kesi', 'wc', 'muzai']
# 长名优先（endignore>ignore，jkaisi1>jkaisi），避免短路
TAF_PRES_TAGS.sort(key=len, reverse=True)
TAF_PRES_RE = re.compile(
    r' ?\[(?:%s)\b[^\]]*\] ?' % '|'.join(re.escape(t) for t in TAF_PRES_TAGS))

# ── 硬名字窗：名前フォント 字体块内的字面名札（如 kouu01 序章
#    `[font face="moji"][mappfont storage="名前フォント.tft"]ナルホド[resetfont]`）
#    与名字宏一致，用【】括上。仅命中含「名前フォント」字样的字体块，不波及
#    Arrow / rubi / color / size 等其它字体强调。
NAMEFONT_RE = re.compile(
    r'(?:\[font[^\]]*\]\[mappfont[^\]]*名前フォント[^\]]*\]'
    r'|\[mappfont[^\]]*名前フォント[^\]]*\]\[font[^\]]*\])'
    r'([^\[\]]*?)\[resetfont\]')


def build_name_map(ks_dir):
    """扫描全部 .ks 的宏定义，提取「名字宏」的字面名。
    判定：宏体含 [font face=name]<字面>[r]（字面）或 [font face=name][emb exp="%name|'默认'"][r]（默认）。"""
    LIT = re.compile(r'\[font\s+face=name\]([^\[\]]*?)\[r\]', re.S)
    EMB = re.compile(r'\[font\s+face=name\]\[emb\s+exp="%name\|[\'"]([^\'"]*)[\'"]"\]\[r\]', re.S)
    nm = {}
    for f in os.listdir(ks_dir):
        if not f.lower().endswith('.ks'):
            continue
        t = K.read_ks(os.path.join(ks_dir, f))
        for m in K.MACRO_DEF.finditer(t):
            name, body = m.group(1), m.group(2)
            lit = LIT.search(body)
            emb = EMB.search(body)
            if lit is not None and lit.group(1).strip():
                nm[name] = lit.group(1).strip()
            elif emb is not None:
                nm[name] = emb.group(1)
    return nm


def slice_label(text, label):
    """取 *label 行到下一个 *label 行之间的正文（label 行本身丢弃）。"""
    label = label.lstrip('*')
    lines = text.split('\n')
    start = None
    for i, ln in enumerate(lines):
        if ln.startswith('*' + label) or ln.startswith('*' + label + '|'):
            start = i + 1
            break
    if start is None:
        return text
    end = len(lines)
    for j in range(start, len(lines)):
        if lines[j].startswith('*'):
            end = j
            break
    return '\n'.join(lines[start:end])


def preprocess(text, name_map):
    """把名字宏 / 标点宏 / hatena / 选项 展开为上屏文本或 [link]…[endlink]，其余标签原样保留。"""
    out = []
    for raw in text.split('\n'):
        line = raw.rstrip('\r')
        s = line.strip()
        if not s or s.startswith('*') or s.startswith(';'):
            # 标签行/注释行不动（但可能含 @ 命令？标签行不含 @ 正文）
            out.append(line)
            continue
        # 纯分隔行（脚本尾部 `////…` 分隔线，非上屏文本）⇒ 跳过
        if set(s) == {'/'}:
            continue
        # ① @cmd attrs → [cmd attrs]（模仿 parse 的归一化，使下面只处理 [] 形）
        if s.startswith('@'):
            line = '[' + s[1:].strip() + ']'
        # ② 选项 link1/link2 的 name 字面 → [link]X[endlink]
        line = re.sub(
            r'\[link1\b[^\]]*?name="\'?([^\'"]*?)\'?"[^\]]*\]',
            lambda m: '[link]%s[endlink]' % m.group(1), line)
        # link2 保留（宏体含 @cm ⇒ 页界，由 macro_events 处理）
        # ③ hatena：裸 → '？？？'；name="'X'" → X；均用【】括上（正文内名札）
        def hat(m):
            a = m.group(1)
            mm = re.search(r'name="\'?([^\'"]*?)\'?"', a)
            return '【%s】' % (mm.group(1) if mm else '？？？')
        line = re.sub(r'\[hatena\b([^\]]*)\]', hat, line)
        # ③b 硬名字窗：名前フォント 字体块内的字面名札 → 用【】括上（与名字宏一致）
        line = NAMEFONT_RE.sub(lambda m: '【%s】' % m.group(1), line)
        # ④ 名字宏 → 字面（先长后短，\b 防 naru 误吞 naru1）；用【】括上（正文内名札）
        if name_map:
            names = sorted(name_map, key=len, reverse=True)
            pat = r'\[(' + '|'.join(re.escape(n) for n in names) + r')\b[^\]]*\]'
            line = re.sub(pat, lambda m: '【%s】' % name_map[m.group(1)], line)
        # ⑤ 标点宏 → 上屏字
        for k, v in TAF_PUNCT.items():
            line = re.sub(r'\[%s\b[^\]]*\]' % re.escape(k), v, line)
        # ⑥ 剥除纯演出/控制标签及其相邻分隔空格（修复 [kao] [naru] → 名字前导空格 泄漏）
        line = TAF_PRES_RE.sub('', line)
        out.append(line)
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dir')
    ap.add_argument('out')
    ap.add_argument('--mode', choices=['dual', 'page'], default='dual')
    ap.add_argument('--files', default='',
                    help='显式文件名（逗号分隔，按此顺序）；不给则按 --order/默认处理')
    ap.add_argument('--order', default='')
    a = ap.parse_args()

    name_map = build_name_map(a.dir)
    macros = K.load_macros(a.dir)
    macro_ev = K.macro_events(macros)
    macro_txt = K.macro_texts(macros)

    # 构建「待处理单元」列表：每项 (stat_name, raw_text)
    # 支持 file:label 切片语法（scenario_1.ks:*m5 → 仅取该 label 到下一个 *label 之间的正文）
    units = []
    if a.files:
        specs = [x for x in a.files.split(',') if x]
        for spec in specs:
            if ':' in spec:
                fname, label = spec.split(':', 1)
                if not fname.endswith('.ks'):
                    fname += '.ks'
                raw = K.read_ks(os.path.join(a.dir, fname))
                units.append((spec, slice_label(raw, label)))
            else:
                fname = spec if spec.endswith('.ks') else spec + '.ks'
                if not os.path.exists(os.path.join(a.dir, fname)):
                    print('!! 缺文件: %s' % fname, file=sys.stderr)
                    continue
                units.append((fname, K.read_ks(os.path.join(a.dir, fname))))
    else:
        order = [x for x in a.order.split(',') if x]
        def key(f):
            for i, o in enumerate(order):
                if o in f:
                    return (i, f)
            return (len(order), f)
        for f in sorted((f for f in os.listdir(a.dir)
                         if f.endswith('.ks') and f not in ('scenario_macro.ks',)), key=key):
            units.append((f, K.read_ks(os.path.join(a.dir, f))))

    allpages, allopts = [], []
    tot = dict(np=0, p=0, l=0, r=0, name=0, link=0, drop_tag=0, mac=0, clear_flush=0, hg=0,
               chars=0, optchars=0)
    drop_names = {}
    for stat, raw in units:
        pp = preprocess(raw, name_map)
        pages, opts, st = K.parse(pp, macro_ev, macro_txt=macro_txt)
        allopts += [(pos + len(allpages), t) for pos, t in opts]
        allpages += pages
        for k in tot:
            tot[k] += st.get(k, 0)
        for nm, c in st.get('drop_names', {}).items():
            drop_names[nm] = drop_names.get(nm, 0) + c
    lines, multi = K.render(allpages, allopts, a.mode)
    segs = sum(len(p) for p in allpages)
    print('文件=%d 页=%d 段=%d 多段页=%d 选项=%d 行=%d 字=%d | np=%d p=%d l=%d r=%d 宏=%d link=%d 清屏收行=%d 未识别标签=%d | 名字宏=%d 段字=%d 选项字=%d'
          % (len(units), len(allpages), segs, multi, len(allopts), len(lines),
             sum(len(x) for x in lines), tot['np'], tot['p'], tot['l'], tot['r'], tot['mac'],
             tot['link'], tot['clear_flush'], tot['drop_tag'], len(name_map),
             tot.get('chars', 0), tot.get('optchars', 0)), file=sys.stderr)
    if drop_names:
        print('丢弃标签: %s' % ' '.join('%s×%d' % (k, v) for k, v in
                                        sorted(drop_names.items(), key=lambda x: -x[1])), file=sys.stderr)
    open(a.out, 'w', encoding='utf-8-sig', newline='\n').write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
