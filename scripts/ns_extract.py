#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""NScripter (nscript.dat) 全文本提取器 —— 「双版对照」口径。

引擎语义（NScripter / clickstr 默认 `\\`）:
  `\\` = 改页（清框）—— A 类：一个文本框结束
  `@`  = 框内等待按键（不清框，文字原地续写）—— B 类：一次点击
  `br` = 命令式换行
⇒ 换行≠换页（skill `S6-lines-dual`）：只交付 `X_全文本_双版对照.txt`
  同一框先列各点击段，再列合并行（单段框不重复）。

用法:
  python ns_extract.py <游戏目录> --out-dir <dir> [--title 名称] [--dry]
"""
import os, re, sys, json, argparse

PLATE_CH = '◆■□★☆▼▲●○◇※◎▽△'
HAS_JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff\uff66-\uff9f]')
CMD_HEAD = re.compile(r'^[A-Za-z_!]')
INLINE_TAG = re.compile(r'!w\d+|!sd|!d\d+|!p\d+|#[0-9a-fA-F]{6}')
OPT_SYS = re.compile(r'^(Ｓｔａｒｔ|スタート|はじめから|最初から|続きから|つづきから|'
                     r'ロード|セーブ|コンフィグ|設定|おわる|終了|終わる|ＥＸＩＴ|'
                     r'おまけ|回想|音楽|ギャラリー|システム|タイトル|ヘルプ|'
                     r'ボリューム|戻る|もどる|ＹＥＳ|ＮＯ|はい|いいえ)$')
MAXCROSS = 8

def decode_dat(path):
    b = open(path, 'rb').read()
    if b'*define' in b or b'*start' in b:
        return b.decode('cp932', 'replace'), 'plain'
    x = bytes(c ^ 0x84 for c in b)
    if b'*define' in x or b'*start' in x:
        return x.decode('cp932', 'replace'), 'xor84'
    return None, 'fail'

def find_script(root):
    for c in [root, os.path.join(root, '本編'), os.path.join(root, 'game')]:
        f = os.path.join(c, 'nscript.dat')
        if os.path.isfile(f):
            return f
    for dp, _, fs in os.walk(root):
        for f in fs:
            if f.lower() == 'nscript.dat':
                return os.path.join(dp, f)
    return None

def is_cmd(s):
    if not s:
        return True
    c = s[0]
    if c in ';#*\\?%:':
        # `:` ＝ NScripter 的命令分隔符 ⇒ 行首 `:` 后面是命令，不是正文
        # （2026-11-02 CLUTCH☆FEVER：`:選択肢 料理コンテストの下準備に行く` 是作者的备忘行）
        return True
    if CMD_HEAD.match(s):
        return True
    if c in '"\'':
        return True
    return False

def plate_of(s):
    t = s.strip()
    if t and t[0] in PLATE_CH and t[-1] in PLATE_CH and len(t) <= 24:
        return True, t.strip(PLATE_CH).replace('\u3000', '').strip()
    return False, None

def looks_bare_name(s, nxt):
    if not s or len(s) > 8 or s[0] in '「『（(【':
        return False
    if s.endswith('\\') or s.endswith('@'):
        return False
    if re.search(r'[。、！？…・」』）)0-9０-９]', s):
        return False
    return bool(nxt) and nxt.lstrip()[:1] in '「『（('

PAIRS = [('「', '」'), ('『', '』'), ('（', '）'), ('【', '】')]

def dangling(t):
    """存在未闭合的开引号 ⇒ 该段跨断点，需接到下一段。"""
    for o, c in PAIRS:
        if t.count(o) > t.count(c):
            return True
    return False

def clean_name(t):
    """名札行：只剔内联标签，保留原有装饰与全角空格。"""
    t = INLINE_TAG.sub('', t)
    return t.strip(' \t\r\n').strip('\u3000').strip()


def clean(t):
    t = INLINE_TAG.sub('', t)
    # ★ 全文空格**原样保留**（U+3000 是原文用字，勿半角化）；首尾由 strip() 一并剥（U+3000 是空白字符）
    t = re.sub(r'[ \t]+', ' ', t)
    return t.strip()

class Rip:
    def __init__(self):
        self.segs = []        # [boxid, text]
        self.opts = []        # [boxid, text]
        self.plates = {}
        self.stats = dict(adv_bs=0, adv_at=0, adv_br=0, boxes=0, multi_boxes=0,
                          opts=0, opt_skipped=0, merged_quote=0, empty=0,
                          names=0, keep_names=1, merge_quote=0)
        self.buf = []
        self.box = 0
        self.plate = ''
        self.pending = ''      # 待并入下一行的人名（名札与正文同框 ⇒ 同一行）
        self.flush_on = {'bs', 'at', 'br'}   # 断行集合：点击版全断；页版只在 'bs' 断

    def _take_pending(self, t):
        if self.pending:
            t = self.pending + t
            self.pending = ''
        return t

    def advance(self, kind):
        if kind == 'bs':
            self.stats['adv_bs'] += 1
        elif kind == 'br':
            self.stats['adv_br'] += 1
        else:
            self.stats['adv_at'] += 1
        if kind not in self.flush_on:
            return                      # 页版：@ / br 不断行，文字继续累加
        t = clean(''.join(self.buf))
        self.buf = []
        if t:
            self.segs.append([self.box, self._take_pending(t), 0])
        else:
            self.stats['empty'] += 1
        if kind == 'bs':
            self.box += 1

    def flush_tail(self):
        t = clean(''.join(self.buf))
        self.buf = []
        if t:
            self.segs.append([self.box, self._take_pending(t), 0])

    def set_plate(self, name, raw=''):
        self.flush_tail()
        self.plate = name
        self.plates[name] = self.plates.get(name, 0) + 1
        if self.stats['keep_names'] and name:
            nt = clean_name(raw) or name
            if nt:
                self.pending = (self.pending + nt) if self.pending else nt
                self.stats['names'] += 1

    def option(self, txt):
        txt = clean(txt).strip('◆■☆★▼●○◇※ 　').strip()
        if not txt:
            return
        if not self.stats.get('keep_sys_opts') and (
                OPT_SYS.match(txt) or OPT_SYS.match(txt.replace(' ', ''))):
            self.stats['opt_skipped'] += 1
            return
        self.stats['opts'] += 1
        self.opts.append([self.box, txt])

CLICKSTR = re.compile(r'^\s*clickstr\s+"([^"]+)"', re.M)
UNDER_ESC = re.compile(r'_(?=[）」』。！？、，,．.])')   # 等待失效标记，不显示
def find_clickstr(text):
    """从 *define 区取 `clickstr "文字列",N` 的字符集（引擎级点击符号，L0）。"""
    m = CLICKSTR.search(text)
    return m.group(1) if m else ''


def split_clickstr(s, clk):
    """按 clickstr 字符切成「一次点击」的段。

    规则（2026-11-02 CLUTCH☆FEVER）：
    - 连续的同组收尾符号并入同一段（`。」`／`……！？』` 只算一次点击）；
    - `_` 前缀 = 引擎的「等待失效」标记 ⇒ 该字符后**不**断段，且 `_` 不显示。
    """
    if not clk:
        return [s]
    out, buf, i, n = [], '', 0, len(s)
    while i < n:
        c = s[i]
        if c == '_' and i + 1 < n and s[i + 1] in clk:
            buf += s[i + 1]                  # 抑制：吞掉 `_`，正常输出该字符
            i += 2
            continue
        buf += c
        i += 1
        if c in clk:
            while i < n and s[i] in clk:     # 连续收尾符并入同一段
                buf += s[i]; i += 1
            out.append(buf); buf = ''
    if buf:
        out.append(buf)
    return out or [s]


def parse(text, keep_names=True, mode='click', clk='', keep_sys_opts=False):
    r = Rip()
    r.flush_on = {'bs'} if mode == 'page' else {'bs', 'at', 'br'}
    r.mode = mode
    r.stats['keep_names'] = 1 if keep_names else 0
    r.stats['keep_sys_opts'] = 1 if keep_sys_opts else 0
    lines = [l.rstrip('\r') for l in text.split('\n')]
    i = 0
    while i < len(lines):
        raw = lines[i]
        i += 1
        s = raw.strip()
        if not s:
            continue
        if s.startswith('*'):
            if r.buf:                # 进入新 *label ⇒ 结页（防跨场景并行）
                r.advance('bs')
            continue
        if s.startswith(';'):
            continue
        # ★ 2026-11-02 Christmas☆Crasher：`csel` 可以**单独成行**，选项写在随后各行
        #   （`csel` / `"行く",*sen1a,` / `"行かない",*sen1b`）。旧正则要求 `csel ` 后有空格 ⇒
        #   裸 `csel` 落到 is_cmd() 被丢弃，34 项选项全丢（opts=0）。
        m = re.match(r'^(select|csel)(?:\s(.*))?$', s)
        if m:
            # ★ 选项面板出现在「当前文本之后」⇒ 先把未收尾的提示框（无 `\` 的 `「選択肢」`）收掉，
            #   否则选项会被标到提示框**之前**（2026-11-02 复核 7月28日に。型写法时补的保险）。
            if r.buf:
                r.advance('bs')
            body = m.group(2) or ''
            while i < len(lines):
                if body and not body.rstrip().endswith(','):
                    break
                nxt = lines[i].strip()
                if not nxt.startswith('"'):
                    break
                body += nxt
                i += 1
            for q in re.findall(r'"([^"]*)"', body):
                if q.startswith('*') or q.startswith(':'):
                    continue
                r.option(q)
            continue
        if s == 'br':
            r.advance('br')
            continue
        if s.split()[0] == 'textclear':
            r.advance('bs')          # 清屏命令＝一页结束（无 `\` 时的隐式断页）
            continue
        # ★ 2026-11-02：`\` / `@` **独占一行**时，is_cmd() 会把 `\` 当命令头直接跳过
        #   ⇒ 上一页与下一页并成一行（Christmas☆Crasher 2 处：`・・・` `\` `face…`）。先处理。
        if all(ch in '\\@ \t' for ch in s):
            for ch in s:
                if ch == '\\':
                    r.advance('bs')
                elif ch == '@':
                    r.advance('at')
            continue
        if is_cmd(s):
            continue
        ok, nm = plate_of(s)
        if ok:
            r.set_plate(nm, raw)
            continue
        if not HAS_JP.search(s) and all(ord(ch) < 0x80 for ch in s):
            continue
        nxt = lines[i] if i < len(lines) else ''
        if looks_bare_name(s, nxt) and not r.buf:
            r.set_plate(s, raw)
            continue
        j = 0
        while j < len(raw):
            c = raw[j]
            if c == '\\':
                r.advance('bs')
                j += 1
                rest = raw[j:].lstrip()
                if rest and re.match(r'^[a-z_][a-z_0-9]*(\s|$|["\',])', rest):
                    break          # 同一行尾随命令（如 `…」\\bg "x.jpg",4`）
                continue
            if c == '@':
                r.advance('at')             # 点击：一次点击 = 一行
                j += 1
                continue
            m2 = INLINE_TAG.match(raw, j)
            if m2:
                j = m2.end(); continue
            r.buf.append(c)
            j += 1
    r.flush_tail()
    if r.pending:
        r.segs.append([r.box, r.pending, 1])
        r.pending = ''
    if clk and mode == 'dual':
        exp, nseg = [], 0
        for boxid, txt, kind in r.segs:
            if kind != 0 or not any(ch in clk for ch in txt):
                exp.append([boxid, txt, kind]); continue
            parts = split_clickstr(txt, clk)
            nseg += len(parts)
            exp.extend([boxid, p, 0] for p in parts)
        r.segs = exp
        r.stats['clickstr'] = clk
        r.stats['click_segs'] = nseg
    # `_` 是引擎的「等待失效」标记（不显示）：clickstr 切段之后再吞掉，
    # 这样 `_」` 既不断段、也不会把 `_` 漏进成品（CLUTCH☆FEVER 3 处，均为 `_）`）。
    n_us = 0
    for sg in r.segs:
        if '_' in sg[1]:
            new = UNDER_ESC.sub('', sg[1])
            if new != sg[1]:
                n_us += sg[1].count('_'); sg[1] = new
    if n_us:
        r.stats['under_esc'] = n_us
    return r

def merge_quotes(segs, stats, enable=False):
    if not enable:
        return [[b, t, 0, k] for b, t, k in segs]
    out = []
    for boxid, t, kind in segs:
        starts_name = bool(t) and t[0] in PLATE_CH      # 下一段另起说话人 ⇒ 不续接
        join = (bool(out) and kind == 0 and out[-1][3] == 0
                and out[-1][2] < MAXCROSS and not starts_name
                and (dangling(out[-1][1]) or t[:1] in '、。，．」』）】'))
        if join:
            out[-1][1] += t
            out[-1][2] += 1
            stats['merged_quote'] += 1
        else:
            out.append([boxid, t, 0, kind])
    return out

def reorder_appendix(text, labels):
    """把指定 `*label` 整块移到末尾（附录：座談会/おまけ等，游戏里在通关后才进入）。

    判据＝**标签块边界**（L0：NScripter 的 `*label` 一律行首），不涉及任何内容判断。
    `labels` 按给定顺序追加到末尾；不存在的标签忽略。
    """
    if not labels:
        return text, []
    lines = text.split('\n')
    head, blocks = [], []
    for ln in lines:
        m = re.match(r'^\*(\w+)', ln)
        if m:
            blocks.append([m.group(1), [ln]])
        elif not blocks:
            head.append(ln)
        else:
            blocks[-1][1].append(ln)
    want = [w for w in labels if any(b[0] == w for b in blocks)]
    keep = [b for b in blocks if b[0] not in want]
    tail = []
    for w in want:
        for b in blocks:
            if b[0] == w:
                tail.extend(b[1])
    out = list(head) + [x for b in keep for x in b[1]] + tail
    return '\n'.join(out), want


def render(r):
    segs = merge_quotes(r.segs, r.stats, enable=bool(r.stats.get('merge_quote')))
    order, boxmap = [], {}
    for boxid, t, _c, kind in segs:
        if boxid not in boxmap:
            boxmap[boxid] = []
            order.append(boxid)
        boxmap[boxid].append((t, kind))
    optmap = {}
    for b, t in r.opts:
        optmap.setdefault(b, []).append(t)
    out = []
    r.stats['boxes'] = len(order)
    for b in order:
        # ★ 2026-11-02 选项插在**下一框之前**（原实现 append 在本框各行之后 ⇒ 差一框：
        #   `csel` 的选项会落到第一个分支台词之后）。self.box 在 advance() 后才 +1，
        #   所以 csel 时记下的 box id 就是「下一框」⇒ 在它之前输出才是正确位置。
        for o in optmap.get(b, []):
            out.append(o)
        items = boxmap[b]
        names = [t for t, k in items if k == 1]
        g = [t for t, k in items if k == 0]
        out.extend(names)
        if len(g) > 1:
            r.stats['multi_boxes'] += 1
            out.extend(g)                  # 点击版各行
            if getattr(r, 'mode', 'dual') == 'dual':
                out.append(''.join(g))     # 页版（同框合并行）
        else:
            out.extend(g)
    for b in optmap:
        if b not in boxmap:
            out.extend(optmap[b])
    return [x for x in out if x.strip()]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dir')
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--title', default=None)
    ap.add_argument('--out-name', default=None,
                    help='成品文件名（不含扩展名）；约定与游戏资源同名')
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--mode', choices=['click', 'page', 'dual'], default='dual',
                    help='click=一次点击一行（@/\\/br 全断）；page=一页一行（只在 \\ 清框处断）')
    ap.add_argument('--names', choices=['keep', 'drop'], default='keep',
                    help='名札处理：keep=并入同一行（正文框内名札，默认）／drop=剔除（独立名字窗）')
    ap.add_argument('--clickstr', choices=['auto', 'off'], default='auto',
                    help='auto=读 *define 的 clickstr，dual 模式下按「引擎点击符」把一框再切成多次点击'
                         '（段行＋合并行）；off=不切')
    ap.add_argument('--keep-sys-opts', action='store_true',
                    help='保留匹配系统菜单词的选项（禁止按内容过滤；特典/おまけ入口等）')
    ap.add_argument('--appendix', default='',
                    help='逗号分隔的 `*label` 名：整块移到末尾（座談会/おまけ等通关后才进入的附录）')
    a = ap.parse_args()
    title = a.title or os.path.basename(os.path.abspath(a.dir))
    sp = find_script(a.dir)
    if not sp:
        print(json.dumps({'title': title, 'error': 'NO_SCRIPT'}, ensure_ascii=False)); sys.exit(2)
    text, how = decode_dat(sp)
    if text is None:
        print(json.dumps({'title': title, 'error': 'DECODE_FAIL'}, ensure_ascii=False)); sys.exit(3)
    app = [x.strip().lstrip('*') for x in a.appendix.split(',') if x.strip()]
    text, app_done = reorder_appendix(text, app)
    clk = find_clickstr(text) if a.clickstr == 'auto' else ''
    r = parse(text, keep_names=(a.names == 'keep'), mode=a.mode, clk=clk,
              keep_sys_opts=a.keep_sys_opts)
    lines = render(r)
    r.stats['lines'] = len(lines)
    info = dict(title=title, script=os.path.relpath(sp, a.dir), decode=how, mode=a.mode, **r.stats)
    if app_done:
        info['appendix'] = app_done
    info['plates'] = dict(sorted(r.plates.items(), key=lambda x: -x[1])[:12])
    if not a.dry:
        os.makedirs(a.out_dir, exist_ok=True)
        out_name = a.out_name or title
        fn = os.path.join(a.out_dir, f'{out_name}.txt')
        with open(fn, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write('\n'.join(lines) + '\n')
        info['out'] = os.path.basename(fn)
    print(json.dumps(info, ensure_ascii=False))

if __name__ == '__main__':
    main()
