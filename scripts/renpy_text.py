#!/usr/bin/env python3
"""Ren'Py .rpy 文本抽取器（通用）

L0 判据（Ren'Py 语义）：
  - 每条 say 语句 = 一个文本框；一次点击 = 一个框 = 一行。
  - 框内换行（字面 \\n）是排版换行 ⇒ 合并进同一行。
  - `{w}`：等一次点击、文本**不清屏**继续同一框 ⇒ 一框多次点击 ⇒ 出双版（段行 + 合并行，合并行确为同框）。
  - `{p}`：等一次点击、**清屏**另起一框 ⇒ 一次点击多框 ⇒ 分段即各框，**不合并**（合并会跨框）。
  - `{nw}`：不等点击，仅排版标记，不切。
  - `{w=…}` / `{p=…}`：定时等待、不等点击。
  - 独立名字窗（show_two_window=True）⇒ 只出正文，不加名。
  - 只收 say ＋ menu 选项；screen / ATL / python 串一律不收。

附加载体（调用方给 arg 下标；L1 结构证据 = 同位置常量、函数签名）：
  - `$ var = "…"` 常量赋值（如试镜台词 `$ line = "…"`，随后 `call checker` 里 `mc "[line]"` 上屏）
  - `funcName(argN)` 取指定实参（如 add_message(subject, sender, body) / add_tweet(avatar, content, date)）
"""
import re
from bisect import bisect_right

BOUNDARY = re.compile(r'(\{w\}|\{p\})')
TAG = re.compile(r'\{[^{}]*\}')
ESC = {'n': '\n', 't': '\t', '\\': '\\', '"': '"', "'": "'", ' ': '\u00a0'}

KEYWORDS = {
    'voice', 'play', 'stop', 'queue', 'show', 'scene', 'hide', 'with', 'jump',
    'call', 'return', 'pause', 'window', 'label', 'menu', 'if', 'elif', 'else',
    'while', 'for', 'python', 'init', 'define', 'default', 'image', 'transform',
    'style', 'screen', 'nvl', 'camera', 'layeredimage', 'translate', 'testcase',
    'extend', 'block', 'use', 'at', 'behind', 'on', 'key', 'expression',
    'centered', 'vcentered', 'rpy', 'font', 'layer', 'add', 'text', 'textbutton',
    'imagebutton', 'bar', 'vbar', 'viewport', 'fixed', 'frame', 'grid', 'vbox',
    'hbox', 'side', 'null', 'timer', 'input', 'imagemap', 'hotspot', 'button',
    'drag', 'draggroup', 'mousearea', 'keymap', 'style_prefix', 'xpos', 'ypos',
    'xalign', 'yalign', 'spacing', 'padding', 'background', 'foreground', 'size',
    'color', 'outlines', 'text_align', 'bold', 'italic', 'underline',
    'line_spacing', 'layout', 'subtitle', 'tooltip', 'action', 'hovered',
    'unhovered', 'selected', 'sensitive', 'activate_sound', 'hover_sound',
    'focus_mask', 'modal', 'zorder', 'at_list', 'align', 'area', 'has', 'contains',
    'pos', 'anchor', 'xsize', 'ysize', 'xmaximum', 'ymaximum', 'xfill', 'yfill',
    'crop', 'crop_relative', 'fit', 'child', 'frame_background', 'vpgrid',
    'cols', 'rows', 'transpose', 'xspacing', 'yspacing', 'allow_underfull',
    'scrollbars', 'mousewheel', 'draggable', 'arrowkeys', 'pagekeys',
    'side_xalign', 'side_yalign', 'spacing_x', 'spacing_y', 'offset',
}
BLOCK_STORY = {'label', 'if', 'elif', 'else', 'while', 'for'}
BLOCK_SKIP = {'python', 'screen', 'image', 'transform', 'style', 'layeredimage',
              'camera', 'translate', 'testcase', 'init', 'menu_item'}


def consume_string(src, i):
    """从 src[i] 起吃掉一个字符串字面量，返回 (原文含引号, 新下标, 消费的换行数)。"""
    q = src[i]
    triple = src.startswith(q * 3, i)
    delim = q * 3 if triple else q
    j = i + len(delim)
    n = len(src)
    nl = 0
    while j < n:
        if src[j] == '\\':
            if j + 1 < n and src[j + 1] == '\n':
                nl += 1
            j += 2
            continue
        if src.startswith(delim, j):
            j += len(delim)
            return src[i:j], j, nl
        if src[j] == '\n':
            nl += 1
        j += 1
    return src[i:], n, nl


def strip_comments(src):
    """注释替换为等长空格（保持偏移与行号）。"""
    out = []
    i = 0
    n = len(src)
    while i < n:
        c = src[i]
        if c in '"\'':
            lit, j, _ = consume_string(src, i)
            out.append(lit)
            i = j
            continue
        if c == '#':
            j = src.find('\n', i)
            if j < 0:
                j = n
            out.append(' ' * (j - i))
            i = j
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def logical_lines(src):
    """→ [(起始行号, 缩进, 去掉注释后的逻辑行文本)]"""
    out = []
    i = 0
    n = len(src)
    line = 1
    while i < n:
        ind = 0
        while i < n and src[i] in ' \t':
            ind += 4 if src[i] == '\t' else 1
            i += 1
        if i >= n:
            break
        if src[i] == '\n':
            i += 1
            line += 1
            continue
        if src[i] == '#':
            k = src.find('\n', i)
            i = n if k < 0 else k + 1
            line += 1
            continue
        start = line
        buf = []
        depth = 0
        while i < n:
            c = src[i]
            if c == '\n':
                i += 1
                line += 1
                if depth == 0:
                    break
                buf.append(' ')
                continue
            if c == '#':
                k = src.find('\n', i)
                if k < 0:
                    i = n
                else:
                    i = k
                continue
            if c in '"\'':
                lit, i, nl = consume_string(src, i)
                buf.append(lit)
                line += nl
                continue
            if c in '([{':
                depth += 1
            elif c in ')]}':
                depth = max(0, depth - 1)
            buf.append(c)
            i += 1
        txt = ''.join(buf).rstrip()
        if txt:
            out.append((start, ind, txt))
    return out


def str_value(lit):
    """去掉引号并解转义。"""
    if lit[:3] in ('"""', "'''"):
        body = lit[3:-3]
    else:
        body = lit[1:-1]
    out = []
    i = 0
    n = len(body)
    while i < n:
        c = body[i]
        if c == '\\' and i + 1 < n:
            nxt = body[i + 1]
            if nxt in ESC:
                out.append(ESC[nxt])
                i += 2
                continue
            out.append(nxt)
            i += 2
            continue
        out.append(c)
        i += 1
    return ''.join(out)


class Parser:
    def __init__(self, chars, consts, interp, skip_labels=()):
        self.chars = chars
        self.consts = consts
        self.interp = interp
        self.skip_labels = set(skip_labels)
        self.stmts = []
        self.unknown = []
        self.dyn_unresolved = []
        self.headers = set()

    def parse(self, path):
        src = path.read_text(encoding='utf-8-sig', errors='replace')
        src = src.replace('\r\n', '\n').replace('\r', '\n')
        stack = []
        skip_ind = None
        for lineno, ind, txt in logical_lines(src):
            if self.skip_labels:
                words = txt.split()
                is_label = len(words) >= 2 and words[0] == 'label' and txt.endswith(':')
                if skip_ind is not None:
                    if is_label and ind <= skip_ind:
                        skip_ind = None
                    else:
                        self.stmts.append(('skip', txt, (path.name, lineno)))
                        continue
                if is_label and words[1].rstrip(':') in self.skip_labels:
                    skip_ind = ind
                    self.stmts.append(('skip', txt, (path.name, lineno)))
                    continue
            while stack and ind <= stack[-1][0]:
                stack.pop()
            ctx = stack[-1][1] if stack else 'story'
            if ctx == 'skip':
                self.stmts.append(('skip', txt, (path.name, lineno)))
                continue
            opens = txt.endswith(':')
            head = txt.split()[0].rstrip(':') if txt.split() else ''
            if ctx == 'menu':
                if txt.startswith(('"', "'")):
                    end = self._lit_end(txt)
                    rest = txt[end:].strip()
                    if (rest.startswith(':') or re.match(r'^if\b.*:\s*$', rest)
                            or re.match(r'^\(.*\)\s*:\s*$', rest)):
                        self.stmts.append(('choice', str_value(txt[:end]), (path.name, lineno)))
                        stack.append((ind, 'story'))
                        continue
                if self._try_say(txt, path, lineno):
                    continue
                self.stmts.append(('menu_stmt', txt, (path.name, lineno)))
                if opens:
                    stack.append((ind, 'skip'))
                continue
            if opens and head == 'menu':
                stack.append((ind, 'menu'))
                self.stmts.append(('menu', txt, (path.name, lineno)))
                continue
            if opens and head in BLOCK_SKIP:
                stack.append((ind, 'skip'))
                self.stmts.append(('skip', txt, (path.name, lineno)))
                continue
            if opens and head in BLOCK_STORY:
                stack.append((ind, 'story'))
                self.stmts.append(('block', txt, (path.name, lineno)))
                continue
            if opens:
                self.headers.add(head)
                stack.append((ind, 'skip'))
                self.stmts.append(('skip', txt, (path.name, lineno)))
                continue
            if self._try_say(txt, path, lineno):
                continue
            if txt.startswith('$'):
                body = txt[1:].strip()
                mm = re.match(r'^([a-zA-Z_]\w*)\s*=\s*("""|\'\'\'|"|\')(.*)\2$', body)
                if mm:
                    val = str_value(mm.group(2) + mm.group(3) + mm.group(2))
                    self.consts[mm.group(1)] = val
                    self.stmts.append(('assign', (mm.group(1), val), (path.name, lineno)))
                self.stmts.append(('python', body, (path.name, lineno)))
                continue
            self.stmts.append(('other', txt, (path.name, lineno)))
        return self

    def _try_say(self, txt, path, lineno):
        if txt.startswith(('"', "'")):
            lit_end = self._lit_end(txt)
            rest = txt[lit_end:].strip()
            self.stmts.append(('say', (None, str_value(txt[:lit_end]), rest), (path.name, lineno)))
            return True
        m = re.match(r'^([a-zA-Z_]\w*)(?=\s|["\'])', txt)
        if not m or m.group(1) in KEYWORDS:
            return False
        name = m.group(1)
        rest_txt = txt[m.end():].lstrip()
        if rest_txt.startswith(('"', "'")):
            lit_end = self._lit_end(rest_txt)
            self.stmts.append(('say', (name, str_value(rest_txt[:lit_end]),
                                       rest_txt[lit_end:].strip()), (path.name, lineno)))
            return True
        if name in self.chars and re.match(r'^[a-zA-Z_]\w*\s*(?:with\s+\w+)?\s*$', rest_txt):
            var = rest_txt.split()[0]
            val = self.consts.get(var)
            if val is None:
                self.dyn_unresolved.append(((path.name, lineno), txt))
            else:
                self.stmts.append(('say', (name, val, ''), (path.name, lineno)))
            return True
        return False

    @staticmethod
    def _lit_end(txt):
        if txt[:3] in ('"""', "'''"):
            d = txt[:3]
            k = txt.find(d, 3)
            return len(txt) if k < 0 else k + 3
        q = txt[0]
        i = 1
        while i < len(txt):
            if txt[i] == '\\':
                i += 2
                continue
            if txt[i] == q:
                return i + 1
            i += 1
        return len(txt)


def _call_args(src, i):
    """src[i]=='('，返回 (顶层实参列表, 右括号后下标)。"""
    depth = 0
    j = i
    args = []
    cur = i + 1
    n = len(src)
    while j < n:
        c = src[j]
        if c in '"\'':
            _, j, _ = consume_string(src, j)
            continue
        if c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
            if depth == 0:
                args.append(src[cur:j])
                return args, j + 1
        elif c == ',' and depth == 1:
            args.append(src[cur:j])
            cur = j + 1
        j += 1
    return args, n


def find_calls(src, specs):
    """扫全文找 `name(arg0, arg1, …)`，取指定位字符串实参。

    specs: {funcname: argindex(0 基)}
    → ([(行号, 值)], [(行号, 原文片段)])；第二项为实参不是字符串字面量的（未解）。
    """
    clean = strip_comments(src)
    starts = [0]
    for m in re.finditer('\n', clean):
        starts.append(m.end())
    found = []
    unresolved = []
    for name, idx in specs.items():
        pat = re.compile(r'(?<![\w.])' + name + r'\s*\(')
        for m in pat.finditer(clean):
            if re.search(r'\bdef\s+$', clean[max(0, m.start() - 24):m.start()]):
                continue
            args, end = _call_args(clean, m.end() - 1)
            ln = bisect_right(starts, m.start())
            if len(args) <= idx:
                unresolved.append((ln, clean[m.start():end][:120]))
                continue
            arg = args[idx].strip()
            if arg.startswith(('"', "'")):
                lit, _, _ = consume_string(arg, 0)
                found.append((ln, str_value(lit)))
            else:
                unresolved.append((ln, clean[m.start():min(end, m.start() + 160)]))
    found.sort()
    return found, unresolved


INTERP_RE = re.compile(r'(?<!\[)\[([A-Za-z_][A-Za-z0-9_.]*)(![a-z])?\]')


def render_text(s, interp, slot_log):
    """剥标签 + 解插值 + 框内换行合并；未知插值按 〔变量名〕 记槽并登记。"""
    s = s.replace('[[', '\x01')

    def rep(m):
        key = m.group(1)
        if key in interp:
            return interp[key]
        slot_log[key] = slot_log.get(key, 0) + 1
        return '〔' + key + '〕'

    s = INTERP_RE.sub(rep, s)
    s = s.replace('\x01', '[')
    s = TAG.sub('', s)
    s = s.replace('\n', ' ')
    s = re.sub(r'[ \t]{2,}', ' ', s).strip()
    return s


def boxes(raw):
    """按 {w}/{p} 切框，返回 [[段…], …]：{w} 在同框累积，{p} 结束当前框。"""
    parts = BOUNDARY.split(raw)
    cur = [parts[0]]
    res = []
    i = 1
    while i < len(parts):
        tag = parts[i]
        nxt = parts[i + 1] if i + 1 < len(parts) else ''
        if tag == '{w}':
            cur.append(nxt)
        else:
            res.append(cur)
            cur = [nxt]
        i += 2
    res.append(cur)
    return res


def extract(files, chars, interp, carriers=None, pure_vars=(), skip_labels=()):
    """→ (行列表, 统计, 插值槽日志, 未解调用, Parser)

    files: Path 列表（按输出顺序传入）
    carriers: {funcname: argindex}
    pure_vars: 纯变量引用的 say（如 'line'）——其值已在赋值处输出，不重复出
    skip_labels: 不属正片的 label（调试用），其整块跳过
    """
    p = Parser(chars, {}, interp, skip_labels)
    for f in files:
        p.parse(f)
    carriers = carriers or {}
    pure_set = {'[' + v + ']' for v in pure_vars}

    per_file = {}
    for k, pl, loc in p.stmts:
        per_file.setdefault(loc[0], []).append((loc[1], 0, k, pl))

    calls = {}
    unresolved_calls = []
    for f in files:
        found, unres = find_calls(f.read_text(encoding='utf-8-sig', errors='replace'), carriers)
        calls[f.name] = found
        unresolved_calls.extend((f.name, ln, txt) for ln, txt in unres)

    out = []
    stats = {'say': 0, 'choice': 0, 'assign': 0, 'call': 0, 'dual': 0,
             'skip_pure': 0, 'lines': 0}
    slot_log = {}
    render_mismatch = 0

    for f in files:
        items = per_file.get(f.name, [])[:]
        for ln, val in calls.get(f.name, []):
            items.append((ln, 2, 'call', val))
        items.sort(key=lambda t: (t[0], t[1]))

        for ln, _, kind, pl in items:
            if kind == 'say':
                who, raw, rest = pl
                if raw.strip() in pure_set:
                    stats['skip_pure'] += 1
                    continue
                stats['say'] += 1
                for segs in boxes(raw):
                    parts = []
                    for x in segs:
                        t = render_text(x, interp, slot_log)
                        if t:
                            parts.append((t, x))
                    if not parts:
                        continue
                    if len(parts) >= 2:
                        stats['dual'] += 1
                        tiles = []
                        for i, (t, x) in enumerate(parts):
                            if i + 1 < len(parts):
                                nxt = parts[i + 1][1]
                                gap = x[-1:].isspace() or nxt[:1].isspace()
                                tiles.append(t + (' ' if gap else ''))
                            else:
                                tiles.append(t)
                        out.extend(tiles)
                        merged = ''.join(tiles)
                        render_mismatch += (merged != render_text(''.join(segs), interp, slot_log))
                        out.append(merged)
                    else:
                        out.append(parts[0][0])
            elif kind == 'choice':
                t = render_text(pl, interp, slot_log)
                if t:
                    out.append(t)
                    stats['choice'] += 1
                    stats['lines'] += 1
            elif kind == 'assign':
                name, val = pl
                if '[' + name + ']' not in pure_set:
                    continue
                t = render_text(val, interp, slot_log)
                if t:
                    out.append(t)
                    stats['assign'] += 1
                    stats['lines'] += 1
            elif kind == 'call':
                t = render_text(pl, interp, slot_log)
                if t:
                    out.append(t)
                    stats['call'] += 1
                    stats['lines'] += 1

    stats['lines'] = len(out)
    stats['render_mismatch'] = render_mismatch
    return out, stats, slot_log, unresolved_calls, p
