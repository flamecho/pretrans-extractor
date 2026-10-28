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
    if c in ';#*\\?%':
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
    t = t.replace('\u3000', ' ')
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
        if OPT_SYS.match(txt) or OPT_SYS.match(txt.replace(' ', '')):
            self.stats['opt_skipped'] += 1
            return
        self.stats['opts'] += 1
        self.opts.append([self.box, txt])

def parse(text, keep_names=True, mode='click'):
    r = Rip()
    r.flush_on = {'bs'} if mode == 'page' else {'bs', 'at', 'br'}
    r.mode = mode
    r.stats['keep_names'] = 1 if keep_names else 0
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
        m = re.match(r'^(select|csel)\s(.*)$', s)
        if m:
            body = m.group(2)
            while body.rstrip().endswith(',') and i < len(lines):
                body += lines[i].strip()
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
                if rest and re.match(r'^[a-z_][a-z_0-9]*(\s|$)', rest):
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
        for o in optmap.get(b, []):
            out.append(o)
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
    a = ap.parse_args()
    title = a.title or os.path.basename(os.path.abspath(a.dir))
    sp = find_script(a.dir)
    if not sp:
        print(json.dumps({'title': title, 'error': 'NO_SCRIPT'}, ensure_ascii=False)); sys.exit(2)
    text, how = decode_dat(sp)
    if text is None:
        print(json.dumps({'title': title, 'error': 'DECODE_FAIL'}, ensure_ascii=False)); sys.exit(3)
    r = parse(text, keep_names=(a.names == 'keep'), mode=a.mode)
    lines = render(r)
    r.stats['lines'] = len(lines)
    info = dict(title=title, script=os.path.relpath(sp, a.dir), decode=how, mode=a.mode, **r.stats)
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
