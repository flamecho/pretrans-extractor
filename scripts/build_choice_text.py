#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CHOICE (KiriKiri KAG) 文本提取 → 提取结果/CHOICE.txt
行粒度（skill §0 / S6-lines-dual）：
  - 点击指令（经验证自 first.ks.txt 宏定义）：
      [plc] -> [p]  (翻页 + 点击)   ; [lc] -> [l]  (同行换行 + 点击)
      [er]  -> 页结束(无点击)        ; [plc2] -> [awsave] (只是存档, 非点击, 忽略)
  - 一页 = 两次翻页(plc/p/er)之间的文本；页内 [lc]/[l] = 多次点击。
  - 单行版（用户要求拆合并行）：一页内每次点击各占一行，不输出整页合并行。
          即「一次点击 = 一行」纯段行版。
  - 选项：[select]..[links2 target=..]文本[endlink]..[endselect] => 选项各占一行(就地)。
  - 人名宏：[emb exp=f.name3] 等 => 替换为脚本默认值(桜木/花梨/カリン)；主角可改名但仍给默认。
  - 富文本：[ruby text="X"] 仅剥读音(基字保留)；其余命令([]...)全剥。
  - 行内变量替换：[emb exp=VAR] => 字面默认值。
输出：UTF-8 BOM / 纯 LF / 0 CR / 0 U+FFFD。
"""
import os, re, sys, glob
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SRC = os.path.join(VNTRANS_HOME, '_work_choice/extracted_text')
OUT = os.path.join(VNTRANS_HOME, '提取结果/CHOICE.txt')

NAME_DEFAULTS = {'name1': '桜木', 'name2': '花梨', 'name3': 'カリン'}

# ---- pass 1: 收集字面量赋值 var='lit' / var="lit" (按基名归一) ----
ASSIGN_RE = re.compile(r"(\w+\.\w+)\s*=\s*'([^']*)'|(\w+\.\w+)\s*=\s*\"([^\"]*)\"")
EMB_RE = re.compile(r'\[emb\s+exp=("?)([^"\]]+)\1\]')
# 引用符を原子的に扱う（exp="...[...]..." のような値内 [ ] を保護）
TAG_RE = re.compile(r"\[(?:[^\[\]\"']|\"[^\"]*\"|'[^']*')*\]")
ISCRIPT_RE = re.compile(r'\[iscript\].*?\[endscript\]', re.S)
# KAG の @コマンド構文 (@tag attr=val ...) を除去（システム設定であり台詞ではない）
AT_RE = re.compile(r"@[A-Za-z_]\w*(?:\s+[A-Za-z_]\w*=(?:\"[^\"]*\"|'[^']*'|[^\s\[\]@]+))*")
COMMENT_RE = re.compile(r'^\s*;')
LABEL_RE = re.compile(r'^\s*\*')

def base(var):
    return var.split('.', 1)[1] if '.' in var else var

# 代码专用文件（无对白标记）里常有空值复位赋值（如 sb.ks 的 sf.name3=''），
# 会污染默认值；扫描赋值时与正文提取一致：跳过无对白标记的文件。
_SKIP_NO_DM = re.compile(r'\[plc\]|\[lc\]|\[er\]|\[p\]|\[l\]')

def scan_assignments():
    amap = {}  # base name -> literal (last wins)
    for path in glob.glob(os.path.join(SRC, '**', '*.ks.txt'), recursive=True):
        try:
            data = open(path, encoding='utf-8').read()
        except Exception:
            continue
        if not _SKIP_NO_DM.search(data):
            continue  # 代码专用文件，其空值复位不代表真实默认
        for m in ASSIGN_RE.finditer(data):
            var = m.group(1) or m.group(3)
            lit = m.group(2) if m.group(2) is not None else m.group(4)
            if var and lit is not None:
                amap[base(var)] = lit
    return amap

def resolve_emb(var, amap):
    b = base(var)
    if b in amap and amap[b]:
        return amap[b]
    if b in NAME_DEFAULTS:
        return NAME_DEFAULTS[b]
    return None

# ---- 标签分类 ----
def tag_kind(tag):
    t = tag.strip('[]').lstrip()
    # 去属性取命令名
    name = re.match(r'(\w+)', t)
    name = name.group(1).lower() if name else ''
    if name in ('plc', 'p'):
        return 'click_page'
    if name in ('lc', 'l'):
        return 'click_line'
    if name == 'er':
        return 'page_end'
    if name in ('r',):
        return 'soft_break'
    if name in ('link', 'links', 'links2'):
        return 'opt_open'
    if name == 'endlink':
        return 'opt_close'
    if name in ('select', 'select2', 'endselect'):
        return 'select_marker'
    if name in ('emb',):
        return 'emb'
    return 'drop'

# 无对白标记的文件 = 纯插件/TJS 代码（rclick_tjs21+.ks / systembutton3fp.ks /
# SavesAnywhere.ks / sb.ks / macro.ks / staffroll.ks / end.ks 等），不是剧本 → 跳过
DIALOGUE_MARKERS = re.compile(r'\[plc\]|\[lc\]|\[er\]|\[p\]|\[l\]')
# 有对白标记但剥离命令/注释/标签后无任何日文叙述（如 scenario/main.ks = CGアルバム画面：
# Gallery 标题 + 页码 1-9 + † MENU † 返回链接 + 按钮 hint），属系统 UI → 跳过
_JP = re.compile(r'[ぁ-んァ-ヶ一-龥]')
def is_pure_ui(raw):
    d = ISCRIPT_RE.sub('', raw)
    d = AT_RE.sub('', d)
    d = re.sub(r'^\s*;.*$', '', d, flags=re.M)
    d = TAG_RE.sub('', d)
    return not _JP.search(d)
# 回想/エンディングリスト等场景跳转菜单项（标题:E06 形式）= 系统 UI，跳过
SCENE_LIST_OPT = re.compile(r'[：:][Ee]\d+$')
# 半角片假名「ｯ」(U+FF6F) → 全角「ッ」(标准半→全，消除化け疑い)
HW_KANA = {'ｯ': 'ッ'}

def process_file(path, amap, out):
    """处理一个 .ks 文件，把提取的行写到 out (list)。返回统计。"""
    stats = dict(pages=0, dual=0, opts=0, lines=0)
    raw = open(path, encoding='utf-8').read()
    # 纯代码文件（无对白标记）跳过
    if not DIALOGUE_MARKERS.search(raw):
        return stats
    # 纯系统 UI（如 CGアルバム画面）：有对白标记但剥离后无日文叙述 → 跳过
    if is_pure_ui(raw):
        return stats
    data = raw
    # 去 iscript 代码块
    data = ISCRIPT_RE.sub('', data)
    # 去 @コマンド (KAG AT-command syntax)
    data = AT_RE.sub('', data)
    # 按物理行处理：去全行注释 / 标签行；行末 \ 续行
    phys = data.split('\n')
    logical = []
    buf = ''
    for line in phys:
        if COMMENT_RE.match(line) or LABEL_RE.match(line):
            continue
        if line.rstrip().endswith('\\'):
            buf += line.rstrip()[:-1]
        else:
            buf += line
            logical.append(buf)
            buf = ''
    if buf:
        logical.append(buf)

    page_segs = []      # 当前页的各次点击段行
    cur_seg = ''        # 当前点击段
    in_opt = False
    opt_buf = ''
    in_select = False   # 在 [select]..[endselect] 内 => 选项
    in_nav = False      # 在导航 [link] 内(无 select) => UI, 文本跳过

    def split_speeches(seg):
        # 同一点击段内若含多个相邻「」对（源脚本中两段之间无点击标签, 如
        #   「A」\n「B[lc]C」  -> 点击段 = 「A」「B ... C」），按“」后接(可选空白)「”
        # 这一相邻对白边界切分, 使每段「…」独立成行。
        # 嵌套引号（「彼は「行く」と」内部」后接非「）不会被误切；[lc]断行已在上游分段。
        parts = re.split(r'(?<=」)\s*(?=「)', seg)
        return [p for p in parts if p.strip() != '']

    def flush_page():
        nonlocal page_segs, cur_seg, stats
        if cur_seg:
            page_segs.append(cur_seg)
            cur_seg = ''
        if not page_segs:
            return
        stats['pages'] += 1
        # 段行（一次点击 = 一个点击段）；再按相邻对白边界切成独立「…」行。
        page_lines = []
        for s in page_segs:
            page_lines.extend(split_speeches(s))
        # 按「…」台词分组输出（双版对照 = 每条被点击切开的台词各自重建整句，而非整页拼接）：
        #   - 完整不跨点击的台词（单段、」」平衡）只出一行，不重复；
        #   - 被点击切开的台词（跨多段、开闭不平衡）=> 各段行后紧跟“这条台词的完整合并行”。
        buf = []          # 当前未闭合台词的各段
        bal = 0           # buf 内 「 - 」 净额
        def flush_speech():
            nonlocal buf, bal
            segs = buf
            buf = []
            bal = 0
            for s in segs:
                out.append(s)
                stats['lines'] += 1
            if len(segs) >= 2:
                out.append(''.join(segs))
                stats['lines'] += 1
                stats['dual'] += 1
        for frag in page_lines:
            buf.append(frag)
            bal += frag.count('「') - frag.count('」')
            if bal <= 0 and '「' in ''.join(buf):
                flush_speech()
        if buf:
            flush_speech()
        page_segs = []

    def push_click():
        nonlocal cur_seg, page_segs
        if cur_seg:
            page_segs.append(cur_seg)
            cur_seg = ''

    for ln in logical:
        # 拆分 text / tag
        pos = 0
        for m in TAG_RE.finditer(ln):
            text = ln[pos:m.start()]
            tag = m.group(0)
            pos = m.end()
            # 处理 text 前段
            if in_opt:
                opt_buf += text
            elif in_nav:
                pass  # 导航链接内文本 = 系统 UI, 跳过
            else:
                cur_seg += text
            # 处理 tag
            kind = tag_kind(tag)
            if kind == 'click_page':
                push_click(); flush_page()
            elif kind == 'click_line':
                push_click()
            elif kind == 'page_end':
                push_click(); flush_page()
            elif kind == 'soft_break':
                pass  # 同行软换行, 不切
            elif kind == 'opt_open':
                if in_select:
                    in_opt = True; opt_buf = ''
                else:
                    in_nav = True  # 导航链接(返回菜单等), 其文本是 UI
            elif kind == 'opt_close':
                if in_opt:
                    if opt_buf.strip() and not SCENE_LIST_OPT.search(opt_buf.strip()):
                        out.append(opt_buf.strip())
                        stats['opts'] += 1; stats['lines'] += 1
                    in_opt = False; opt_buf = ''
                in_nav = False
            elif kind == 'emb':
                mv = EMB_RE.match(tag)
                var = mv.group(2) if mv else ''
                val = resolve_emb(var, amap)
                if val is None:
                    val = '〔未解析:%s〕' % var
                if in_opt:
                    opt_buf += val
                elif in_nav:
                    pass  # 导航链接内宏 = UI
                else:
                    cur_seg += val
            elif kind == 'select_marker':
                nm = re.match(r'(\w+)', tag.strip('[]').lstrip())
                nm = nm.group(1).lower() if nm else ''
                in_select = (nm != 'endselect')
            else:
                pass  # drop
        # 行尾剩余 text
        tail = ln[pos:]
        if in_opt:
            opt_buf += tail
        elif in_nav:
            pass  # 导航链接内文本 = UI
        else:
            cur_seg += tail
    # EOF flush
    push_click(); flush_page()
    return stats

def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    amap = scan_assignments()
    # 文件名排序：first.ks 优先，其余按路径
    files = glob.glob(os.path.join(SRC, '**', '*.ks.txt'), recursive=True)
    files.sort(key=lambda p: (os.path.basename(p) != 'first.ks.txt', p))
    out = []
    tot = dict(pages=0, dual=0, opts=0, lines=0)
    for f in files:
        s = process_file(f, amap, out)
        for k in tot:
            tot[k] += s[k]
    # 半角片假名→全角 (消除化け疑い)
    out = [''.join(HW_KANA.get(c, c) for c in line) for line in out]
    # 写文件 (BOM + LF)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as g:
        for line in out:
            g.write(line + '\n')
    print('files=%d lines=%d pages=%d options=%d (段行-only, no whole-page merged line)' % (
        len(files), tot['lines'], tot['pages'], tot['opts']))
    print('wrote', OUT)

if __name__ == '__main__':
    main()
