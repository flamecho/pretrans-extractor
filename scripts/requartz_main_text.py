#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[JP]Re;quartz (PC / Adobe AIR, B-cluster engine) .an 剧本 -> 全文本（双版对照）

格式（L0 自引擎定义）：
  * 翻页/一次点击  = 反斜杠（main.an: [char2macro char=\ name=plc]，plc=[p][er]=清屏+等点击）
  * 行内软换行     = [r]（合并，不当新行）
  * 行点击等待     = @  （char2macro char=@ name=l；页内段界）
  * [er]/[s]       = 引擎 rec_page_break=false，不当文本框界，只剥标签
对话块（格式A）：
  [fkds?_?? text="NAME"] [voice fn=..] [h_voice] <台词> [end_h_voice] \
  - NAME 经 rec_ch "NAME )" 渲染在文本框顶部气泡标签 -> 按独立气泡标签口径剔除（--with-name 可加回）
  - <台词> = [h_voice]..[end_h_voice] 之间的内联文本（其间 [fg..] 等标签剥除）
旁白/独白（格式B，special_story 等）：
  直接在 mes 层内联，[r]=软换行，@=段界，\=翻页；[mono_n] 设无说话人
选项：
  [sentakusiN] 后用 [link ..][ch text="选项"][endlink] 承载，逐条输出
"""
import re, os, sys, glob

# ---- 标签切分：交替返回 文本 / [tag] ----
TAG = re.compile(r'(\[[^\]]*\])')

def split_tags(s):
    out, last = [], 0
    for m in TAG.finditer(s):
        if m.start() > last:
            out.append(s[last:m.start()])
        out.append(m.group(1))
        last = m.end()
    if last < len(s):
        out.append(s[last:])
    return out

def tag_name(t):
    m = re.match(r'\[/?([A-Za-z_][A-Za-z0-9_]*)', t)
    return m.group(1).lower() if m else None

def tag_attr(t, key):
    m = re.search(key + r'\s*=\s*"([^"]*)"', t)
    if m: return m.group(1)
    m = re.search(key + r'\s*=\s*([^\s\]]+)', t)
    return m.group(1) if m else None

class Box:
    def __init__(self):
        self.segs = []          # list of (speaker, text)
        self.cur_spk = None
        self.cur_txt = []
        self.in_hv = False
        self.in_link = False
        self.lines_out = []      # 本框产出的行（含选项）
        self.choice_pending = None
    def _push_seg(self):
        if self.cur_txt:
            txt = ''.join(self.cur_txt).strip()
            if txt:
                self.segs.append((self.cur_spk, txt))
            self.cur_txt = []
    def add_text(self, t, is_choice=False):
        if is_choice:
            self.lines_out.append(('choice', None, t.strip()))
        else:
            self.cur_txt.append(t)
    def seg_break(self):
        self._push_seg()
    def flush(self, sink):
        self._push_seg()
        segs = self.segs
        if not segs and not self.lines_out:
            return
        # 选项独立成行
        for kind, spk, t in self.lines_out:
            if kind == 'choice':
                sink.append(t)
        # 正文段
        if len(segs) == 1:
            spk, t = segs[0]
            sink.append(t)
        elif len(segs) >= 2:
            for spk, t in segs:
                sink.append(t)
            sink.append(''.join(t for _, t in segs))
        # 清空
        self.segs = []; self.lines_out = []; self.cur_txt = []; self.cur_spk = None

def parse_file(path, sink, with_name=False):
    box = Box()
    speaker = None
    for raw in open(path, encoding='utf-8'):
        line = raw.rstrip('\n').rstrip('\r')
        ls = line.strip()
        if not ls:
            continue
        if ls.startswith(';') or ls.startswith('&'):
            continue            # 整行注释 / 脚本变量赋值
        if ls.startswith('*'):  # 标签行：剥 *label 令牌，保留其后正文
            m = re.match(r'\*[A-Za-z0-9_]+', ls)
            line = ls[m.end():] if m else ls[1:]
            if not line.strip():
                continue
        # 反斜杠 = 翻页
        if '\\' in line:
            pre = line.split('\\', 1)[0]
            if pre.strip():
                _process(pre, box, speaker, with_name)
            box.flush(sink)
            speaker = None
            continue
        _process(line, box, speaker, with_name)
    box.flush(sink)

def _process(line, box, speaker, with_name):
    # 切分为 文本 / 标签
    parts = split_tags(line)
    for p in parts:
        if not p.startswith('['):
            s = p.strip()
            if not s or s.startswith(';') or s.startswith('&'):
                continue                     # 丢弃行尾注释片段 / 脚本表达式
            subs = s.split('@')               # @ = 行点击等待 = 页内段界
            for i, sub in enumerate(subs):
                if not sub:
                    continue
                box.add_text(sub)
                if i < len(subs) - 1:
                    box.seg_break()
            continue
        name = tag_name(p)
        if name is None:
            continue
        if name == 'h_voice':
            box.in_hv = True
        elif name == 'end_h_voice':
            box.in_hv = False
            box.seg_break()
        elif name == 'mono_n':
            speaker = None
            box.cur_spk = None
        elif name in ('fkds1','fkds2','fkds3') or name.startswith('fkds'):
            sp = tag_attr(p, 'text')
            if sp:
                speaker = sp
                box.cur_spk = sp if with_name else None
        elif name == 'link':
            box.in_link = True
        elif name == 'endlink':
            box.in_link = False
        elif name == 'ch':
            t = tag_attr(p, 'text')
            if t is not None:
                if box.in_link:
                    box.add_text(t, is_choice=True)
                else:
                    box.add_text(t)
        elif name == 'r':
            pass  # 软换行 -> 合并
        elif name == 'at' or name == 'l':
            box.seg_break()
        # 其它标签（voice/fg/er/s/bgm/img/lay/rec_ch 等）一律剥除

def main():
    base = '_work_requartz_main/air/scenario'
    out = '提取结果/[JP]Re;quartz.txt'
    with_name = '--with-name' in sys.argv
    files = ['ss_000','2nd_000','leito','motoi','saiki','special_story']
    sink = []
    for fn in files:
        p = os.path.join(base, fn + '.an')
        if os.path.exists(p):
            parse_file(p, sink, with_name)
            print('  %-14s -> %d lines so far' % (fn, len(sink)), file=sys.stderr)
    os.makedirs('提取结果', exist_ok=True)
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(sink) + '\n')
    print('TOTAL lines: %d' % len(sink))

if __name__ == '__main__':
    main()
